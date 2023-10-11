from aws_cdk import Duration, aws_apigateway
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as _lambda
from cdk_monitoring_constructs import CustomMetricGroup, ErrorRateThreshold, LatencyThreshold, MetricStatistic, MonitoringFacade
from constructs import Construct

from infrastructure.product import constants


class CrudMonitoring(Construct):

    def __init__(
        self,
        scope: Construct,
        id_: str,
        crud_api: aws_apigateway.RestApi,
        db: dynamodb.Table,
        idempotency_table: dynamodb.Table,
        functions: list[_lambda.Function],
    ) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self._build_high_level_dashboard(crud_api)
        self._build_low_level_dashboard(db, idempotency_table, functions)

    def _build_high_level_dashboard(self, crud_api: aws_apigateway.RestApi):
        high_level_facade = MonitoringFacade(self, f'{self.id_}HighFacade')
        high_level_facade.add_large_header('Products REST API High Level Dashboard')
        high_level_facade.monitor_api_gateway(
            api=crud_api,
            add5_xx_fault_rate_alarm={'internal_error': ErrorRateThreshold(max_error_rate=1)},
        )
        metric_factory = high_level_facade.create_metric_factory()
        create_metric = metric_factory.create_metric(
            metric_name='CreateProductEvents',
            namespace=constants.METRICS_NAMESPACE,
            statistic=MetricStatistic.N,
            dimensions_map={constants.METRICS_DIMENSION_KEY: constants.SERVICE_NAME},
            label='create product events',
            period=Duration.days(1),
        )

        get_metric = metric_factory.create_metric(
            metric_name='GetProductEvents',
            namespace=constants.METRICS_NAMESPACE,
            statistic=MetricStatistic.N,
            dimensions_map={constants.METRICS_DIMENSION_KEY: constants.SERVICE_NAME},
            label='get product events',
            period=Duration.days(1),
        )
        list_metric = metric_factory.create_metric(
            metric_name='ListProductsEvents',
            namespace=constants.METRICS_NAMESPACE,
            statistic=MetricStatistic.N,
            dimensions_map={constants.METRICS_DIMENSION_KEY: constants.SERVICE_NAME},
            label='list products events',
            period=Duration.days(1),
        )
        delete_metric = metric_factory.create_metric(
            metric_name='DeleteProductEvents',
            namespace=constants.METRICS_NAMESPACE,
            statistic=MetricStatistic.N,
            dimensions_map={constants.METRICS_DIMENSION_KEY: constants.SERVICE_NAME},
            label='delete product events',
            period=Duration.days(1),
        )

        group = CustomMetricGroup(metrics=[create_metric, get_metric, list_metric, delete_metric], title='Daily Product Requests')
        high_level_facade.monitor_custom(metric_groups=[group], human_readable_name='Daily KPIs', alarm_friendly_name='KPIs')

    def _build_low_level_dashboard(self, db: dynamodb.Table, idempotency_table: dynamodb.Table, functions: list[_lambda.Function]):
        low_level_facade = MonitoringFacade(self, f'{self.id_}LowFacade')
        low_level_facade.add_large_header('Products REST API Low Level Dashboard')
        for func in functions:
            low_level_facade.monitor_lambda_function(
                lambda_function=func,
                add_latency_p90_alarm={'p90': LatencyThreshold(max_latency=Duration.seconds(3))},
            )
            low_level_facade.monitor_log(
                log_group_name=func.log_group.log_group_name,
                human_readable_name='Error logs',
                pattern='ERROR',
                alarm_friendly_name='error logs',
            )

        low_level_facade.monitor_dynamo_table(table=db, billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST)
        low_level_facade.monitor_dynamo_table(table=idempotency_table, billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST)