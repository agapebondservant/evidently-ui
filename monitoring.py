import datetime

from evidently import ColumnMapping
from evidently.metrics import ColumnDriftMetric
from evidently.metrics import ColumnSummaryMetric
from evidently.metrics import DatasetDriftMetric
from evidently.metrics import DatasetMissingValuesMetric
from evidently.report import Report
from evidently.test_preset import DataDriftTestPreset
from evidently.test_suite import TestSuite
from evidently.ui.dashboards import CounterAgg
from evidently.ui.dashboards import DashboardPanelCounter
from evidently.ui.dashboards import DashboardPanelPlot
from evidently.ui.dashboards import PanelValue
from evidently.ui.dashboards import PlotType
from evidently.ui.dashboards import ReportFilter
from evidently.ui.workspace import Workspace
from evidently.ui.workspace import WorkspaceBase
import os
import pandas as pd
import logging
import time

WORKSPACE = "workspace"
WORKSPACE_PROJECT_NAME = "Tanzu Realtime Anomaly Detection Project"
WORKSPACE_PROJECT_DESCRIPTION = "Monitors credit card transactional data in near realtime."
DATASOURCE_URL_SERVER = os.getenv('inference_cache_server') or 'http://gfanomaly-server.tanzudatatap.com/gemfire-api/v1'
DATASOURCE_REGION = os.getenv('inference_snapshot_region') or 'mds-region-greenplum'
DATASOURCE_FETCH_LIMIT = os.getenv('inference_cache_server_fetch_size') or 1600
DATASOURCE_URL = f'{DATASOURCE_URL_SERVER}/{DATASOURCE_REGION}?limit={DATASOURCE_FETCH_LIMIT}'
EVIDENTLY_BATCH_SIZE = os.getenv('monitoring_batch_size') or 100
EVIDENTLY_BATCH_PROCESSING_INTERVAL = os.getenv('monitoring_batch_processing_interval') or 10
EVIDENTLY_NUMERICAL_FEATURES = ['id', 'time_passed', 'amount', 'latitude', 'longitude', 'is_fraud_flag', 'training_run_timestamp', 'cls_weight']
DEMO_MODE = True


def generate_datasets(demo_mode=False):
    logging.info(f"Fetch from url: {DATASOURCE_URL}")
    data = pd.json_normalize(pd.read_json(DATASOURCE_URL)[DATASOURCE_REGION])
    data.sort_values(['training_run_timestamp', 'id'], ascending=False, inplace=True)
    current_data = reference_data = None
    if demo_mode:
        current_data = data[0: round(len(data)/2)]
        reference_data = data[round(len(data)/2): len(data)]
    else:
        dfs = dict(tuple(data.groupby('training_run_timestamp')))
        it = iter(dfs.values())
        current_data = next(it, None)
        reference_data = next(it, None)
    return current_data, reference_data


def create_report(current_data, reference_data):
    data_drift_report = Report(
        metrics=[
            DatasetDriftMetric(),
            DatasetMissingValuesMetric(),
            ColumnDriftMetric(column_name="amount", stattest="wasserstein"),
            ColumnSummaryMetric(column_name="amount"),
            ColumnDriftMetric(column_name="time_passed", stattest="wasserstein"),
            ColumnSummaryMetric(column_name="time_passed"),
        ],
        timestamp=datetime.datetime.now(),
    )

    column_mapping = ColumnMapping()
    column_mapping.numerical_features = EVIDENTLY_NUMERICAL_FEATURES
    data_drift_report.run(reference_data=reference_data, current_data=current_data, column_mapping=column_mapping)
    return data_drift_report


def create_test_suite(current_data, reference_data):
    data_drift_test_suite = TestSuite(
        tests=[DataDriftTestPreset()],
        timestamp=datetime.datetime.now(),
    )

    column_mapping = ColumnMapping()
    column_mapping.numerical_features = EVIDENTLY_NUMERICAL_FEATURES
    data_drift_test_suite.run(reference_data=reference_data, current_data=current_data, column_mapping=column_mapping)
    return data_drift_test_suite


def create_project(workspace: WorkspaceBase):
    project = workspace.create_project(WORKSPACE_PROJECT_NAME)
    project.description = WORKSPACE_PROJECT_DESCRIPTION
    project.dashboard.add_panel(
        DashboardPanelCounter(
            filter=ReportFilter(metadata_values={}, tag_values=[]),
            agg=CounterAgg.NONE,
            title="Credit Card Transactions Dataset",
        )
    )
    project.dashboard.add_panel(
        DashboardPanelCounter(
            title="Model Calls",
            filter=ReportFilter(metadata_values={}, tag_values=[]),
            value=PanelValue(
                metric_id="DatasetMissingValuesMetric",
                field_path=DatasetMissingValuesMetric.fields.current.number_of_rows,
                legend="count",
            ),
            text="count",
            agg=CounterAgg.SUM,
            size=1,
        )
    )
    project.dashboard.add_panel(
        DashboardPanelCounter(
            title="Share of Drifted Features",
            filter=ReportFilter(metadata_values={}, tag_values=[]),
            value=PanelValue(
                metric_id="DatasetDriftMetric",
                field_path="share_of_drifted_columns",
                legend="share",
            ),
            text="share",
            agg=CounterAgg.LAST,
            size=1,
        )
    )
    project.dashboard.add_panel(
        DashboardPanelPlot(
            title="Dataset Quality",
            filter=ReportFilter(metadata_values={}, tag_values=[]),
            values=[
                PanelValue(metric_id="DatasetDriftMetric", field_path="share_of_drifted_columns", legend="Drift Share"),
                PanelValue(
                    metric_id="DatasetMissingValuesMetric",
                    field_path=DatasetMissingValuesMetric.fields.current.share_of_missing_values,
                    legend="Missing Values Share",
                ),
            ],
            plot_type=PlotType.LINE,
        )
    )
    project.dashboard.add_panel(
        DashboardPanelPlot(
            title="Amount: Wasserstein drift distance",
            filter=ReportFilter(metadata_values={}, tag_values=[]),
            values=[
                PanelValue(
                    metric_id="ColumnDriftMetric",
                    metric_args={"column_name.name": "amount"},
                    field_path=ColumnDriftMetric.fields.drift_score,
                    legend="Drift Score",
                ),
            ],
            plot_type=PlotType.BAR,
            size=1,
        )
    )
    project.dashboard.add_panel(
        DashboardPanelPlot(
            title="Time-elapsed: Wasserstein drift distance",
            filter=ReportFilter(metadata_values={}, tag_values=[]),
            values=[
                PanelValue(
                    metric_id="ColumnDriftMetric",
                    metric_args={"column_name.name": "time_passed"},
                    field_path=ColumnDriftMetric.fields.drift_score,
                    legend="Drift Score",
                ),
            ],
            plot_type=PlotType.BAR,
            size=1,
        )
    )
    project.save()
    return project


def create_workspace_project(workspace: str):
    ws = Workspace.create(workspace)

    current_data_total, reference_data_total = generate_datasets(demo_mode=DEMO_MODE)

    project = create_project(ws)

    if current_data_total is not None and reference_data_total is not None:
        max_rows = min(len(current_data_total), len(reference_data_total))

        logging.info(f"Number of rows fetched: {max_rows}")

        for i in range(0, max_rows, int(EVIDENTLY_BATCH_SIZE)):
            logging.info(f"Generating monitored data - batch [0 - {i+int(EVIDENTLY_BATCH_SIZE)}]...")

            # ws.delete_project(project.id) if project else True
            # project = create_project(ws)

            current_data = current_data_total[: i + int(EVIDENTLY_BATCH_SIZE)]
            reference_data = reference_data_total[: i + int(EVIDENTLY_BATCH_SIZE)]

            report = create_report(current_data, reference_data)
            ws.add_report(project.id, report)

            test_suite = create_test_suite(current_data, reference_data)
            ws.add_test_suite(project.id, test_suite)

            logging.info(f"Monitoring data for batch [0 - {i+int(EVIDENTLY_BATCH_SIZE)}] generated.")

            time.sleep(int(EVIDENTLY_BATCH_PROCESSING_INTERVAL))
    else:
        logging.error("No data snapshots found.")


create_workspace_project(WORKSPACE)
