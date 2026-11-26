import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useLocation, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, Database, FilePlus2,
  GitFork, Plus,
  Search, Snowflake, Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { evalApi } from '@/api/eval.api';
import {
  useDatasetMutation, useDatasets, useSelectedDataset,
} from '@/features/evaluation/hooks/useEval';
import {
  EmptyState, Field, LockedBanner, Panel, Pill, PrincipalNote, SelectBox,
  Stat, TextField, downloadText,
} from '@/features/evaluation/components/EvalPrimitives';
import { CorpusSection } from '@/features/evaluation/components/construction/CorpusSection';
import { ItemsSection } from '@/features/evaluation/components/construction/ItemsSection';
import { SyntheticSection } from '@/features/evaluation/components/construction/SyntheticSection';
import { ChunkingSection } from '@/features/evaluation/components/construction/ChunkingSection';
import { IndexSection } from '@/features/evaluation/components/construction/IndexSection';
import { PoolingSection } from '@/features/evaluation/components/construction/PoolingSection';
import { AgreementSection } from '@/features/evaluation/components/construction/AgreementSection';
import { DiffSection } from '@/features/evaluation/components/construction/DiffSection';
import { VersionPicker } from '@/features/evaluation/components/construction/VersionPicker';
import { GateSection, type GateChapter } from '@/features/evaluation/components/GateSection';
import { preferredVersion } from '@/features/evaluation/components/DatasetPicker';
import { fmtTime, shortHash } from '@/features/evaluation/lib/evalStats';
import { useEvalStore } from '@/store/eval.store';
import type { DatasetBundle, DatasetSummary } from '@/types/eval';

const PAGE_SIZE = 8;

type SpineTab = 'collect' | 'ask' | 'index' | 'judge' | 'gate' | 'freeze';
type AskTab = 'items' | 'synthetic';
type IndexTab = 'chunking' | 'index';
type JudgeTab = 'pool' | 'audit';
type FreezeTab = 'lifecycle' | 'diff';

const SPINE: SpineTab[] = ['collect', 'ask', 'index', 'judge', 'gate', 'freeze'];

const SUB_TABS: Record<SpineTab, string[]> = {
  collect: [],
  ask:     ['items', 'synthetic'],
  index:   ['chunking', 'index'],
  judge:   ['pool', 'audit'],
  gate:    ['checks', 'split', 'power', 'profile'],
  freeze:  ['lifecycle', 'diff'],
};

const SUB_DEFAULT: Record<SpineTab, string> = {
  collect: '',
  ask: 'items',
  index: 'chunking',
  judge: 'pool',
  gate: 'checks',
  freeze: 'lifecycle',
};

function resolveSpineTab(raw: string | null, sub: string | null): SpineTab {
  if (raw === 'build' && (sub === 'corpus' || !sub)) return 'collect';
  if (raw === 'build') return 'ask';
  if (raw === 'inspect') return 'index';
  if (raw === 'label') return 'judge';
  if (raw === 'versions') return 'freeze';
  if (raw && SPINE.includes(raw as SpineTab)) return raw as SpineTab;
  return 'ask';
}

function useSpineParams(): [SpineTab, string, (t: SpineTab, s?: string) => void] {
  const [params, setParams] = useSearchParams();
  const rawTab = params.get('tab');
  const rawSub = params.get('sub');
  const tab = resolveSpineTab(rawTab, rawSub);
  const allowed = SUB_TABS[tab];
  const sub = allowed.length === 0
    ? ''
    : (rawSub && allowed.includes(rawSub) ? rawSub : (rawTab === 'build' && rawSub === 'items' ? 'items' : rawTab === 'build' && rawSub === 'synthetic' ? 'synthetic' : SUB_DEFAULT[tab]));

  const setTab = (next: SpineTab, nextSub?: string) => {
    const merged = new URLSearchParams(params);
    merged.set('tab', next);
    const resolved = nextSub ?? SUB_DEFAULT[next];
    if (resolved) merged.set('sub', resolved);
    else merged.delete('sub');
    setParams(merged);
  };
  return [tab, sub, setTab];
}

export function DatasetConstructionPage() {
  const { datasetId } = useParams<{ datasetId?: string }>();
  return datasetId ? <DatasetDetail datasetId={datasetId} /> : <DatasetList />;
}

/* ── Listing ─────────────────────────────────────────────────────────────── */

function DatasetList() {
  const datasets = useDatasets();
  const navigate = useNavigate();
  const select = useEvalStore((s) => s.select);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [lang, setLang] = useState('en');

  const create = useDatasetMutation(
    (vars: { name: string; lang: string }) => evalApi.createDataset(vars),
    'Dataset created',
  );

  const importDataset = useDatasetMutation(async (file: File) => {
    const format = file.name.split('.').pop()?.toLowerCase();
    if (format !== 'json' && format !== 'jsonl' && format !== 'csv')
      throw new Error('Choose a JSON, JSONL, or CSV file.');
    return evalApi.importDataset({
      format,
      content: (await file.text()).replace(/^\uFEFF/, ''),
      name: file.name.slice(0, -(format.length + 1)),
      language: lang,
    });
  }, 'Labeled dataset imported');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = datasets.data ?? [];
    if (!q) return rows;
    return rows.filter((d) => `${d.name} ${d.id} ${d.lang}`.toLowerCase().includes(q));
  }, [datasets.data, query]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const slice = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  function openDataset(d: DatasetSummary, version?: number) {
    const v = version ?? preferredVersion(d.versions);
    if (v == null) return;
    select(d.id, v);
    const snapshot = d.versions.find((row) => row.version === v);
    const qs = snapshot?.items ? 'tab=ask&sub=items' : 'tab=collect';
    navigate(`/evaluation/dataset/${encodeURIComponent(d.id)}?${qs}`, { state: { version: v } });
  }

  function goCreated(bundle: DatasetBundle) {
    select(bundle.meta.id, bundle.manifest.version);
    navigate(`/evaluation/dataset/${encodeURIComponent(bundle.meta.id)}`);
  }

  return (
    <div className="space-y-5">
      <header className="work-heading">
        <div>
          <h2>Datasets</h2>
          <p>Manage the questions, passages and judgments behind your experiments.</p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <Plus size={16} /> Add dataset
        </Button>
      </header>
      <div className="work-tools">
        <span className="work-caption">
          Library <b>{datasets.data?.length ?? '…'}</b>
        </span>
        <label className="work-search">
          <Search size={15} />
          <input
            aria-label="Search datasets"
            placeholder="Search datasets"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
          />
        </label>
      </div>

      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) {
            setName('');
            setLang('en');
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add dataset</DialogTitle>
            <DialogDescription>Import a labeled file or create an empty dataset.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <label className="work-upload">
              Import labeled dataset <span>JSON, JSONL or CSV</span>
              <input
                aria-label="Import labeled dataset"
                type="file"
                accept=".json,.jsonl,.csv"
                disabled={importDataset.isPending}
                onChange={(e) => {
                  const file = e.currentTarget.files?.[0];
                  e.currentTarget.value = '';
                  if (file) importDataset.mutate(file, { onSuccess: goCreated });
                }}
              />
            </label>
            <Field label="New dataset name">
              <TextField
                autoFocus
                placeholder="e.g. HR policies (en)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && name.trim() && !create.isPending) {
                    create.mutate(
                      { name: name.trim(), lang },
                      {
                        onSuccess: (bundle) => {
                          setName('');
                          setOpen(false);
                          goCreated(bundle);
                        },
                      },
                    );
                  }
                }}
              />
            </Field>
            <Field label="Language">
              <SelectBox
                value={lang}
                onChange={setLang}
                options={[
                  { value: 'en', label: 'English' },
                  { value: 'ar', label: 'Arabic' },
                ]}
              />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              className="gap-1.5"
              disabled={!name.trim() || create.isPending}
              onClick={() =>
                create.mutate(
                  { name: name.trim(), lang },
                  {
                    onSuccess: (bundle) => {
                      setName('');
                      setOpen(false);
                      goCreated(bundle);
                    },
                  },
                )
              }
            >
              <Plus className="h-3.5 w-3.5" /> Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {datasets.isLoading ? (
        <div className="space-y-2" aria-label="Loading datasets">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-md border border-white/8 bg-card/30" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-white/15 bg-card/20 px-6 py-16 text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-neon/10 text-neon">
            <Database className="h-7 w-7" />
          </span>
          <p className="mt-4 font-display text-lg font-semibold">
            {query ? 'No matches' : 'No datasets yet'}
          </p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
            {query
              ? 'Try a different search, or clear the filter.'
              : 'Add a labeled file or create your first dataset.'}
          </p>
          {!query && (
            <Button size="sm" variant="neon" className="mt-5 h-10 gap-1.5" onClick={() => setOpen(true)}>
              <Plus className="h-3.5 w-3.5" /> New dataset
            </Button>
          )}
        </div>
      ) : (
        <>
          <div className="work-list">
            <table>
              <thead>
                <tr>
                  <th>Dataset</th>
                  <th>Questions</th>
                  <th className="wide-col">Passages</th>
                  <th>Version</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {slice.map((d) => {
                  const v = d.versions[d.versions.length - 1];
                  return (
                    <tr key={d.id}>
                      <td>
                        <button className="work-name" onClick={() => openDataset(d, v?.version)}>
                          <Database size={17} />
                          <span>
                            {d.name}
                            <small>{d.lang}</small>
                          </span>
                        </button>
                      </td>
                      <td>{v?.items ?? 0}</td>
                      <td className="wide-col">{v?.documents ?? 0}</td>
                      <td>v{v?.version ?? 1}</td>
                      <td>
                        <span className="work-state">{v?.status ?? 'draft'}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/8 bg-card/20 px-3 py-2">
              <p className="text-xs text-muted-foreground">
                Showing {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, filtered.length)} of{' '}
                {filtered.length}
              </p>
              <div className="flex items-center gap-1">
                <Button
                  aria-label="Previous page"
                  size="sm"
                  variant="ghost"
                  className="h-8 w-8 p-0"
                  disabled={safePage <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
                  <Button
                    key={n}
                    size="sm"
                    variant={n === safePage ? 'default' : 'ghost'}
                    className={cn(
                      'h-8 min-w-[32px] px-2 font-mono text-xs',
                      n === safePage && 'shadow-glow-sm',
                    )}
                    onClick={() => setPage(n)}
                  >
                    {n}
                  </Button>
                ))}
                <Button
                  aria-label="Next page"
                  size="sm"
                  variant="ghost"
                  className="h-8 w-8 p-0"
                  disabled={safePage >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

type DatasetView = { tab: SpineTab; sub: string; label: string };
const datasetSections: { name: string; views: DatasetView[] }[] = [
  {
    name: 'Content',
    views: [
      { tab: 'ask', sub: 'items', label: 'Questions' },
      { tab: 'collect', sub: '', label: 'Passages' },
      { tab: 'ask', sub: 'synthetic', label: 'Candidate questions' },
      { tab: 'index', sub: 'chunking', label: 'Passage chunking' },
      { tab: 'index', sub: 'index', label: 'Search index' },
    ],
  },
  {
    name: 'Review',
    views: [
      { tab: 'judge', sub: 'pool', label: 'Relevance judgments' },
      { tab: 'judge', sub: 'audit', label: 'Reviewer agreement' },
      { tab: 'gate', sub: 'split', label: 'Split audit' },
      { tab: 'gate', sub: 'power', label: 'Statistical power' },
      { tab: 'gate', sub: 'profile', label: 'Coverage' },
    ],
  },
  {
    name: 'Versions',
    views: [
      { tab: 'freeze', sub: 'lifecycle', label: 'Version history' },
      { tab: 'freeze', sub: 'diff', label: 'Compare versions' },
      { tab: 'gate', sub: 'checks', label: 'Readiness checks' },
    ],
  },
];

function DatasetDetail({ datasetId }: { datasetId: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const datasets = useDatasets();
  const { datasetId: selectedId, version, select } = useEvalStore();
  const summary = datasets.data?.find((d) => d.id === datasetId);
  const stateVersion = (location.state as { version?: number } | null)?.version;
  const queryVersion = Number(new URLSearchParams(location.search).get('v'));
  const intendedVersion =
    stateVersion ?? (Number.isFinite(queryVersion) && queryVersion > 0 ? queryVersion : undefined);

  useEffect(() => {
    if (!summary?.versions.length) return;
    const fallback =
      preferredVersion(summary.versions) ?? summary.versions[summary.versions.length - 1].version;
    const fromNav =
      intendedVersion != null && summary.versions.some((v) => v.version === intendedVersion)
        ? intendedVersion
        : null;
    if (selectedId !== datasetId) {
      select(datasetId, fromNav ?? fallback);
      return;
    }
    if (!summary.versions.some((v) => v.version === version)) select(datasetId, fromNav ?? fallback);
  }, [datasetId, summary, selectedId, version, select, intendedVersion]);

  const { data: bundle, isLoading } = useSelectedDataset();

  const ready = bundle && bundle.meta.id === datasetId;

  const [tab, subtab, setTab] = useSpineParams();
  const askTab = (subtab as AskTab) || 'items';
  const indexTab = (subtab as IndexTab) || 'chunking';
  const judgeTab = (subtab as JudgeTab) || 'pool';
  const gateTab = (subtab as GateChapter) || 'checks';
  const freezeTab = (subtab as FreezeTab) || 'lifecycle';

  const section =
    datasetSections.find((group) => group.views.some((v) => v.tab === tab && v.sub === subtab)) ??
    datasetSections[0];
  const pending = ready
    ? bundle.items.find((i) => i.metadata?.pair_id && !i.metadata?.pair_reviewed)
    : undefined;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <Button
            size="sm"
            variant="ghost"
            className="mt-0.5 h-9 gap-1.5 text-xs"
            onClick={() => navigate('/evaluation/dataset')}
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Datasets
          </Button>
          <div className="min-w-0">
            <h3 className="font-display text-2xl font-semibold tracking-tight">
              {summary?.name ?? datasetId}
            </h3>
            <p className="text-xs text-muted-foreground">
              {ready
                ? `${bundle.items.length} questions · ${bundle.corpus.length.toLocaleString()} passages`
                : datasetId}
            </p>
          </div>
        </div>
        {summary && (
          <div className="flex flex-wrap items-center gap-2">
            <Pill>{summary.lang}</Pill>
            <VersionPicker
              compact
              align="end"
              className="w-[17.5rem]"
              versions={summary.versions}
              value={version ?? summary.versions[summary.versions.length - 1]?.version ?? 1}
              onChange={(v) => select(datasetId, v)}
            />
          </div>
        )}
      </div>

      {!summary && !datasets.isLoading && (
        <Panel title="Unknown dataset" icon={Database}>
          <EmptyState icon={Database} title="This dataset is not on the lab">
            It may have been removed, or the Eval Lab API is on a different stack.
          </EmptyState>
        </Panel>
      )}

      {(isLoading || (summary && !ready)) && (
        <div className="h-48 animate-pulse rounded-2xl border border-white/8 bg-card/30" />
      )}

      {ready && (
        <>
          {bundle.manifest.status === 'frozen' && (
            <LockedBanner>
              <strong className="text-foreground">v{bundle.manifest.version} is frozen</strong> — content is
              read-only. Label audits and pools remain available; fork a new version to change documents,
              items or labels.
            </LockedBanner>
          )}

          <div className="work-detail-nav">
            <nav aria-label="Dataset sections">
              {datasetSections.map((group) => (
                <button
                  key={group.name}
                  aria-current={group === section ? 'page' : undefined}
                  onClick={() => setTab(group.views[0].tab, group.views[0].sub)}
                >
                  {group.name}
                </button>
              ))}
            </nav>
            <select
              aria-label={section.name + ' view'}
              value={tab + '|' + subtab}
              onChange={(e) => {
                const view = section.views.find((v) => v.tab + '|' + v.sub === e.target.value);
                if (view) setTab(view.tab, view.sub);
              }}
            >
              {section.views.map((v) => (
                <option key={v.tab + v.sub} value={v.tab + '|' + v.sub}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>
          {section.name !== 'Versions' && pending && bundle.manifest.status !== 'frozen' && (
            <Button
              onClick={() =>
                navigate(
                  '/evaluation/experiments/paired?pair=' +
                    encodeURIComponent(String(pending.metadata?.pair_id)),
                )
              }
            >
              Continue pair review <ArrowRight size={15} />
            </Button>
          )}

          <div key={`${tab}-${subtab}`} className="animate-fade-in space-y-4">
            {tab === 'collect' && <CorpusSection bundle={bundle} />}
            {tab === 'ask' && askTab === 'items' && <ItemsSection bundle={bundle} />}
            {tab === 'ask' && askTab === 'synthetic' && <SyntheticSection bundle={bundle} />}
            {tab === 'index' && indexTab === 'chunking' && <ChunkingSection bundle={bundle} />}
            {tab === 'index' && indexTab === 'index' && <IndexSection bundle={bundle} />}
            {tab === 'judge' && judgeTab === 'pool' && <PoolingSection bundle={bundle} />}
            {tab === 'judge' && judgeTab === 'audit' && <AgreementSection bundle={bundle} />}
            {tab === 'gate' && <GateSection bundle={bundle} chapter={gateTab} />}
            {tab === 'freeze' && freezeTab === 'lifecycle' && (
              <VersionPanel bundle={bundle} versions={summary?.versions ?? []} />
            )}
            {tab === 'freeze' && freezeTab === 'diff' && <DiffSection bundle={bundle} />}
          </div>
        </>
      )}
    </div>
  );
}

function VersionPanel({ bundle, versions }: { bundle: DatasetBundle; versions: DatasetSummary['versions'] }) {
  const { meta, manifest } = bundle;
  const select = useEvalStore((s) => s.select);
  const frozen = manifest.status === 'frozen';
  const [changelog, setChangelog] = useState('');
  const freeze = useDatasetMutation(() => evalApi.freeze(meta.id, manifest.version), `v${manifest.version} frozen`);
  const fork = useDatasetMutation((c: string) => evalApi.fork(meta.id, manifest.version, c), 'New draft version created');
  const tampered = frozen && manifest.content_hash !== bundle.current_hash;
  const synthetic = bundle.items.filter((i) => i.origin === 'synthetic').length;
  const negatives = bundle.items.reduce((n, i) => n + i.judged_nonrelevant.length, 0);
  const rows = versions.length
    ? versions
    : [{ ...manifest, items: bundle.items.length, documents: bundle.corpus.length }];

  async function exportJsonl() {
    const out = await evalApi.export(meta.id, manifest.version);
    downloadText(`${meta.id}-v${manifest.version}-${shortHash(out.content_hash)}.jsonl`, out.golden_jsonl, 'application/x-ndjson');
  }

  return (
    <Panel
      title="Lifecycle"
      icon={frozen ? Snowflake : FilePlus2}
      subtitle="Choose a snapshot, then freeze it or fork a new draft."
      actions={<Pill tone={frozen ? 'info' : 'warn'}>{manifest.status}</Pill>}
    >
      <div className="space-y-4 text-xs">
        <Field label="Version">
          <VersionPicker
            versions={rows}
            value={manifest.version}
            onChange={(v) => select(meta.id, v)}
          />
        </Field>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="Items" value={bundle.items.length} sub={synthetic ? `${synthetic} synthetic` : undefined} />
          <Stat label="Documents" value={bundle.corpus.length} sub={`${negatives} explicit 0-judgements`} />
          <Stat label="Content hash" value={shortHash(bundle.current_hash)} />
          <Stat label={frozen ? 'Frozen at' : 'Created'} value={fmtTime(frozen ? manifest.frozen_at : manifest.created_at)} />
        </div>
        <dl className="space-y-1 font-mono text-[11px]">
          {frozen && <div className="flex justify-between gap-2"><dt className="text-muted-foreground">frozen hash</dt><dd className={tampered ? 'text-red-400' : ''}>{shortHash(manifest.content_hash)}</dd></div>}
          {manifest.parent_version && <div className="flex justify-between gap-2"><dt className="text-muted-foreground">forked from</dt><dd>v{manifest.parent_version}</dd></div>}
        </dl>
        {manifest.changelog && <p className="rounded-md bg-white/5 p-2 text-muted-foreground">{manifest.changelog}</p>}

        {!frozen ? (
          <Button size="sm" variant="neon" className="gap-1.5" disabled={freeze.isPending} onClick={() => freeze.mutate(undefined)}>
            <Snowflake className="h-3.5 w-3.5" /> Freeze v{manifest.version}
          </Button>
        ) : (
          <div className="flex flex-wrap items-end gap-2">
            <Field label="Changelog" className="min-w-[240px] flex-1">
              <TextField placeholder="What changes in the new version?" value={changelog} onChange={(e) => setChangelog(e.target.value)} />
            </Field>
            <Button size="sm" className="h-9 gap-1.5" disabled={fork.isPending} onClick={() => fork.mutate(changelog)}>
              <GitFork className="h-3.5 w-3.5" /> Fork to v{manifest.version + 1}
            </Button>
          </div>
        )}
        <Button size="sm" variant="ghost" className="gap-1.5 text-xs" onClick={exportJsonl}>
          <Download className="h-3.5 w-3.5" /> Export golden JSONL
        </Button>

        <PrincipalNote title="Data versioning & immutability">
          A number is only meaningful as a pair: <strong>(system, dataset hash)</strong>. Freezing records the hash; every
          run stores the hash it scored. Changing a frozen set means <strong>forking</strong> — never editing history —
          so “v2 recall” always refers to the same questions. Freeze → Diff shows what a fork did to comparability.
        </PrincipalNote>
      </div>
    </Panel>
  );
}
