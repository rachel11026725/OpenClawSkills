"""Ported tool registry for the Python porting workspace."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToolEntry:
    name: str
    description: str = ""
    mcp: bool = False
    simple: bool = False

    def execute(self, prompt: str) -> str:
        return f"Mirrored tool '{self.name}': {prompt}"


def _tool(name: str, description: str = "", mcp: bool = False, simple: bool = False) -> ToolEntry:
    return ToolEntry(name=name, description=description, mcp=mcp, simple=simple)


PORTED_TOOLS: list[ToolEntry] = [
    _tool("MCPTool", "Primary MCP tool", mcp=True),
    _tool("FileReader", "Read files from filesystem"),
    _tool("FileWriter", "Write files to filesystem"),
    _tool("CodeAnalyzer", "Analyze code structure"),
    _tool("TestRunner", "Run test suites"),
    _tool("Debugger", "Debug code execution"),
    _tool("Formatter", "Format source code"),
    _tool("Linter", "Lint source code"),
    _tool("SecurityScanner", "Scan for security issues"),
    _tool("DependencyChecker", "Check project dependencies"),
    _tool("DocumentationGenerator", "Generate documentation"),
    _tool("CodeRefactorer", "Refactor code"),
    _tool("SearchEngine", "Search codebase"),
    _tool("DatabaseQuery", "Query databases"),
    _tool("APIClient", "Make API calls"),
    _tool("WebScraper", "Scrape web pages"),
    _tool("DataTransformer", "Transform data"),
    _tool("CacheManager", "Manage cache"),
    _tool("LogAnalyzer", "Analyze logs"),
    _tool("MetricsCollector", "Collect metrics"),
    _tool("AlertManager", "Manage alerts"),
    _tool("DeploymentTool", "Deploy applications"),
    _tool("ContainerManager", "Manage containers"),
    _tool("CloudProvider", "Cloud provider tools"),
    _tool("StorageManager", "Manage storage"),
    _tool("NetworkAnalyzer", "Analyze network"),
    _tool("PerformanceProfiler", "Profile performance"),
    _tool("MemoryAnalyzer", "Analyze memory"),
    _tool("CrashReporter", "Report crashes"),
    _tool("ErrorTracker", "Track errors"),
    _tool("VersionControl", "Version control operations"),
    _tool("BranchManager", "Manage branches"),
    _tool("MergeConflictResolver", "Resolve merge conflicts"),
    _tool("CodeReviewer", "Review code"),
    _tool("PullRequestManager", "Manage pull requests"),
    _tool("IssueTracker", "Track issues"),
    _tool("ProjectManager", "Manage projects"),
    _tool("TaskScheduler", "Schedule tasks"),
    _tool("WorkflowEngine", "Run workflows"),
    _tool("PipelineRunner", "Run CI/CD pipelines"),
    _tool("BuildSystem", "Build projects"),
    _tool("PackageManager", "Manage packages"),
    _tool("EnvironmentManager", "Manage environments"),
    _tool("ConfigurationManager", "Manage configuration"),
    _tool("SecretsManager", "Manage secrets"),
    _tool("AuthProvider", "Authentication provider"),
    _tool("PermissionManager", "Manage permissions"),
    _tool("AuditLogger", "Log audit events"),
    _tool("ComplianceChecker", "Check compliance"),
    _tool("VulnerabilityScanner", "Scan vulnerabilities"),
    _tool("PatchManager", "Manage patches"),
    _tool("BackupManager", "Manage backups"),
    _tool("RestoreManager", "Restore from backup"),
    _tool("ExportTool", "Export data"),
    _tool("ImportTool", "Import data"),
    _tool("DataMigrator", "Migrate data"),
    _tool("SchemaValidator", "Validate schemas"),
    _tool("DataCleaner", "Clean data"),
    _tool("DataTranslator", "Translate data"),
    _tool("ReportGenerator", "Generate reports"),
    _tool("DashboardBuilder", "Build dashboards"),
    _tool("ChartCreator", "Create charts"),
    _tool("GraphAnalyzer", "Analyze graphs"),
    _tool("TreeNavigator", "Navigate trees"),
    _tool("IndexBuilder", "Build indexes"),
    _tool("QueryOptimizer", "Optimize queries"),
    _tool("CacheWarmer", "Warm caches"),
    _tool("SessionManager", "Manage sessions"),
    _tool("TokenManager", "Manage tokens"),
    _tool("CertificateManager", "Manage certificates"),
    _tool("SSLChecker", "Check SSL"),
    _tool("DNSResolver", "Resolve DNS"),
    _tool("LoadBalancer", "Load balancing"),
    _tool("RateLimiter", "Rate limiting"),
    _tool("CircuitBreaker", "Circuit breaker"),
    _tool("RetryHandler", "Handle retries"),
    _tool("TimeoutManager", "Manage timeouts"),
    _tool("HealthChecker", "Check health"),
    _tool("ServiceDiscovery", "Service discovery"),
    _tool("RegistryClient", "Registry client"),
    _tool("MessageBroker", "Message broker"),
    _tool("EventEmitter", "Emit events"),
    _tool("StreamProcessor", "Process streams"),
    _tool("BatchProcessor", "Process batches"),
    _tool("ParallelExecutor", "Execute in parallel"),
    _tool("WorkerPool", "Worker pool"),
    _tool("TaskQueue", "Task queue"),
    _tool("JobScheduler", "Schedule jobs"),
    _tool("CronManager", "Manage cron jobs"),
    _tool("TimerManager", "Manage timers"),
    _tool("WatcherService", "Watch for changes"),
    _tool("FileWatcher", "Watch files"),
    _tool("DirectoryScanner", "Scan directories"),
    _tool("PatternMatcher", "Match patterns"),
    _tool("RegexEngine", "Regex operations"),
    _tool("TemplateEngine", "Template rendering"),
    _tool("CodeGenerator", "Generate code"),
    _tool("MockService", "Mock services", simple=True),
    _tool("StubFactory", "Create stubs", simple=True),
    _tool("TestFixture", "Test fixtures"),
    _tool("BenchmarkRunner", "Run benchmarks"),
    _tool("ProfilerTool", "Profile code"),
    _tool("TracingTool", "Trace execution"),
    _tool("SpanRecorder", "Record spans"),
    _tool("MCPResourceFetcher", "Fetch MCP resources", mcp=True),
    _tool("MCPToolInvoker", "Invoke MCP tools", mcp=True),
    _tool("MCPServerManager", "Manage MCP servers", mcp=True),
]

if len(PORTED_TOOLS) < 100:
    raise RuntimeError(f"Expected >= 100 tools, got {len(PORTED_TOOLS)}")
