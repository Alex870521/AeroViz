from diagrams import Cluster, Diagram
from diagrams.onprem.aggregator import Fluentd
from diagrams.onprem.analytics import Spark
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Nginx
from diagrams.onprem.queue import Kafka

with Diagram("DataPlot flowchart", show=True, filename="assets/figure/diagram"):
	ingress = Nginx("ABC")

	metrics = Prometheus("metric")
	metrics << Grafana("monitoring")

	with Cluster("Service Cluster"):
		grpcsvc = [
			Server("grpc1"),
			Server("grpc2"),
			Server("grpc3")]

	with Cluster("Sessions HA"):
		primary = Redis("session")
		primary - Redis("replica") << metrics
		grpcsvc >> primary

	with Cluster("Database HA"):
		primary = PostgreSQL("users")
		primary - PostgreSQL("replica") << metrics
		grpcsvc >> primary

	aggregator = Fluentd("logging")
	aggregator >> Kafka("stream") >> Spark("analytics")

	ingress >> grpcsvc >> aggregator
