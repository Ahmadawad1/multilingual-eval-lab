import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { ServerCrash, Terminal } from 'lucide-react';
import { DatasetPicker, preferredVersion } from '@/features/evaluation/components/DatasetPicker';
import { useDatasets, useEvalStatus } from '@/features/evaluation/hooks/useEval';
import { useEvalStore } from '@/store/eval.store';

const PAGE_INTRO: { prefix: string; title: string; blurb: string }[] = [
  {
    prefix: '/evaluation/retrieval',
    title: 'Retrieval',
    blurb: 'Probe one query, score a split, then compare A/B runs.',
  },
];

export function EvaluationLayout() {
  const { pathname } = useLocation();
  const status = useEvalStatus();
  const datasets = useDatasets();
  const { datasetId, version, select } = useEvalStore();
  const onGoldenSets = pathname.startsWith('/evaluation/dataset');
  const onExperiments = pathname.startsWith('/evaluation/experiments');
  const onNormalization = pathname.startsWith('/evaluation/normalization');
  const rows = datasets.data ?? [];
  const intro = PAGE_INTRO.find((p) => pathname.startsWith(p.prefix));

  useEffect(() => {
    if (!datasets.data) return;
    const currentOk = rows.some((d) => d.id === datasetId && d.versions.some((v) => v.version === version));
    if (currentOk) return;
    const first = rows[0];
    const preferred = first ? preferredVersion(first.versions) : undefined;
    if (first && preferred != null) select(first.id, preferred);
    else if (datasetId) select(null, null);
  }, [datasets.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const offline = status.isError;
  const showDatasetSelect = !onGoldenSets &&
    (!onExperiments || pathname === '/evaluation/experiments/paired') &&
    !onNormalization && pathname !== '/evaluation/stats' && rows.length > 0;

  return (
    <div>
      {(intro || showDatasetSelect) && (
        <div className={intro ? "work-heading mb-5" : "mb-5 flex flex-wrap items-end justify-end gap-4"}>
          {intro && (
            <div className="min-w-0 flex-1">
              <h2>{intro.title}</h2>
              <p className="text-sm text-muted-foreground">{intro.blurb}</p>
            </div>
          )}
          {showDatasetSelect && (
            <DatasetPicker
              datasets={rows}
              datasetId={datasetId}
              version={version}
              onChange={select}
            />
          )}
        </div>
      )}

      {offline && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/[0.06] p-4 text-sm">
          <ServerCrash className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
          <div className="space-y-1.5">
            <p className="font-medium">The Eval Lab API is not reachable.</p>
            <p className="text-xs text-muted-foreground">
              {onNormalization
                ? 'Arabic Norm only needs the Eval Lab API. Start it locally, then reload:'
                : 'It runs on the lean evaluation stack, not the dev stack. Start it, then reload:'}
            </p>
            <pre className="flex items-center gap-2 rounded-md bg-black/40 px-3 py-2 font-mono text-xs text-foreground">
              <Terminal className="h-3.5 w-3.5 text-neon" />
              {'.\\scripts\\start.ps1'}
            </pre>
            <p className="text-xs text-muted-foreground">
              Open the local lab at <code className="font-mono">127.0.0.1:8000/evaluation/dataset</code>.
            </p>
          </div>
        </div>
      )}

      <Outlet />
    </div>
  );
}
