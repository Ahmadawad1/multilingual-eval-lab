import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { EvaluationLayout }        from '@/pages/evaluation/EvaluationLayout';
import { DatasetConstructionPage } from '@/pages/evaluation/DatasetConstructionPage';
import { DataLabPage }             from '@/pages/evaluation/DataLabPage';
import { RetrievalEvalPage }       from '@/pages/evaluation/RetrievalEvalPage';
import { NormalizationPage }       from '@/pages/evaluation/NormalizationPage';
import { ExperimentsPage, ExperimentCreatePage, ExperimentDetailPage } from '@/pages/evaluation/ExperimentsPage';
import { StatsLabPage }            from '@/pages/evaluation/StatsLabPage';
import { GenerationPage }          from '@/pages/evaluation/GenerationPage';
import { JudgeLabPage }            from '@/pages/evaluation/JudgeLabPage';
import { ReleaseGatePage }         from '@/pages/evaluation/ReleaseGatePage';
import { PairedStudyPage } from '@/pages/evaluation/PairedStudyPage';

const evaluationRoute: RouteObject = {
  path: 'evaluation',
  element: <EvaluationLayout />,
  children: [
    { index: true,          element: <Navigate to="/evaluation/dataset" replace /> },
    { path: 'dataset',      element: <DatasetConstructionPage /> },
    { path: 'dataset/:datasetId', element: <DatasetConstructionPage /> },
    { path: 'data-lab',     element: <DataLabPage /> },
    { path: 'retrieval',    element: <RetrievalEvalPage /> },
    { path: 'normalization', element: <NormalizationPage /> },
    { path: 'experiments', element: <ExperimentsPage /> },
    { path: 'experiments/new', element: <ExperimentCreatePage /> },
    { path: 'experiments/paired', element: <PairedStudyPage /> },
    { path: 'experiments/:experimentId', element: <ExperimentDetailPage /> },
    { path: 'stats',        element: <StatsLabPage /> },
    { path: 'generation',   element: <GenerationPage /> },
    { path: 'judges',       element: <JudgeLabPage /> },
    { path: 'gate',         element: <ReleaseGatePage /> },
    { path: 'learn',        element: <Navigate to="/evaluation/stats" replace /> },
  ],
};

export const router = createBrowserRouter([{ element: <AppLayout />, children: [
  { index: true, element: <Navigate to="/evaluation/dataset" replace /> }, evaluationRoute,
] }]);
