"""SmartWealthAI application package (MVP pipeline).

Submodules
----------
download_fundamentals
    CLI for the fundamentals download spike (SEC + edgartools).
sec_client
    SEC EDGAR REST connector.
edgartools_client
    Standardized annual statements via edgartools.
lake_paths
    Raw-zone path builders.
universe
    Versioned universe preset loading.
fixture_lake
    Hermetic test fixtures for CI.
"""

__version__ = "0.1.0"
