"""
AeroViz MCP Server

Provides AI assistants with access to aerosol data processing capabilities.

Installation:
    pip install mcp

Usage in Claude Code settings (~/.claude/settings.json):
{
  "mcpServers": {
    "aeroviz": {
      "command": "python",
      "args": ["/path/to/AeroViz/AeroViz/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/AeroViz"
      }
    }
  }
}
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Create server instance
server = Server("aeroviz")

# Supported instruments metadata
SUPPORTED_INSTRUMENTS = {
    "AE33": {"description": "Aethalometer - Black carbon at 7 wavelengths", "freq": "1min"},
    "AE43": {"description": "Aethalometer - Black carbon at 7 wavelengths", "freq": "1min"},
    "BC1054": {"description": "Black carbon monitor", "freq": "1min"},
    "MA350": {"description": "MicroAeth - Portable black carbon", "freq": "1min"},
    "SMPS": {"description": "Scanning Mobility Particle Sizer - Size distribution 10-1000nm", "freq": "6min"},
    "APS": {"description": "Aerodynamic Particle Sizer - Size distribution 0.5-20μm", "freq": "6min"},
    "GRIMM": {"description": "Optical particle counter", "freq": "6min"},
    "TEOM": {"description": "Tapered Element Oscillating Microbalance - PM mass", "freq": "6min"},
    "BAM1020": {"description": "Beta Attenuation Monitor - PM mass", "freq": "1h"},
    "NEPH": {"description": "Nephelometer - Scattering coefficients", "freq": "5min"},
    "Aurora": {"description": "Aurora nephelometer - Scattering at 3 wavelengths", "freq": "1min"},
    "OCEC": {"description": "OC/EC analyzer - Organic/Elemental carbon", "freq": "1h"},
    "Xact": {"description": "XRF analyzer - Heavy metals (Fe, Zn, Pb, etc.)", "freq": "1h"},
    "IGAC": {"description": "Ion chromatograph - Water-soluble ions", "freq": "1h"},
    "VOC": {"description": "VOC analyzer - Volatile organic compounds", "freq": "1h"},
    "Q-ACSM": {"description": "Aerosol Chemical Speciation Monitor", "freq": "30min"},
    "EPA": {"description": "EPA air quality data", "freq": "1h"},
    "Minion": {"description": "Minion sensor", "freq": "1h"},
}


@server.list_tools()
async def list_tools():
    """List available AeroViz tools."""
    return [
        Tool(
            name="list_instruments",
            description="List all supported aerosol instruments in AeroViz",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="read_instrument_data",
            description="Read and process aerosol instrument data with automatic QC",
            inputSchema={
                "type": "object",
                "properties": {
                    "instrument": {
                        "type": "string",
                        "description": "Instrument name (e.g., AE33, SMPS, APS, TEOM)",
                        "enum": list(SUPPORTED_INSTRUMENTS.keys())
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory path containing raw data files"
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO format (e.g., 2024-01-01)"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in ISO format (e.g., 2024-12-31)"
                    },
                    "mean_freq": {
                        "type": "string",
                        "description": "Averaging frequency (default: 1h)",
                        "default": "1h"
                    },
                    "qc": {
                        "type": "boolean",
                        "description": "Apply quality control (default: true)",
                        "default": True
                    },
                    "reset": {
                        "type": "boolean",
                        "description": "Force reprocess from raw files (default: false)",
                        "default": False
                    }
                },
                "required": ["instrument", "path", "start", "end"]
            }
        ),
        Tool(
            name="get_data_summary",
            description="Get summary statistics of processed aerosol data",
            inputSchema={
                "type": "object",
                "properties": {
                    "instrument": {
                        "type": "string",
                        "description": "Instrument name",
                        "enum": list(SUPPORTED_INSTRUMENTS.keys())
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory path containing raw data files"
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO format"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in ISO format"
                    }
                },
                "required": ["instrument", "path", "start", "end"]
            }
        ),
        Tool(
            name="get_instrument_info",
            description="Get detailed information about a specific instrument",
            inputSchema={
                "type": "object",
                "properties": {
                    "instrument": {
                        "type": "string",
                        "description": "Instrument name",
                        "enum": list(SUPPORTED_INSTRUMENTS.keys())
                    }
                },
                "required": ["instrument"]
            }
        ),
        Tool(
            name="calculate_optical_properties",
            description="Calculate optical properties (AAE, SAE, SSA, etc.) from aerosol data",
            inputSchema={
                "type": "object",
                "properties": {
                    "absorption_data": {
                        "type": "string",
                        "description": "JSON string of absorption coefficient data"
                    },
                    "scattering_data": {
                        "type": "string",
                        "description": "JSON string of scattering coefficient data (optional)"
                    }
                },
                "required": ["absorption_data"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""

    if name == "list_instruments":
        result = []
        for inst, info in SUPPORTED_INSTRUMENTS.items():
            result.append(f"- **{inst}**: {info['description']} (freq: {info['freq']})")
        return [TextContent(
            type="text",
            text="# Supported Instruments in AeroViz\n\n" + "\n".join(result)
        )]

    elif name == "get_instrument_info":
        instrument = arguments.get("instrument")
        if instrument not in SUPPORTED_INSTRUMENTS:
            return [TextContent(type="text", text=f"Unknown instrument: {instrument}")]

        info = SUPPORTED_INSTRUMENTS[instrument]

        # Get additional info from meta config
        from AeroViz.rawDataReader.config.supported_instruments import meta
        meta_info = meta.get(instrument, {})

        result = f"""# {instrument}

**Description**: {info['description']}
**Native Frequency**: {info['freq']}
**File Patterns**: {', '.join(meta_info.get('pattern', ['Unknown']))}

## Usage Example
```python
from AeroViz import RawDataReader

df = RawDataReader(
    instrument='{instrument}',
    path='/path/to/data',
    start='2024-01-01',
    end='2024-12-31',
    mean_freq='1h',
    qc=True
)
```
"""
        # Add MDL info if available
        if 'MDL' in meta_info:
            result += "\n## Minimum Detection Limits (MDL)\n"
            for elem, mdl in list(meta_info['MDL'].items())[:10]:
                if mdl is not None:
                    result += f"- {elem}: {mdl} ng/m³\n"
            if len(meta_info['MDL']) > 10:
                result += f"- ... and {len(meta_info['MDL']) - 10} more elements\n"

        return [TextContent(type="text", text=result)]

    elif name == "read_instrument_data":
        try:
            from AeroViz import RawDataReader

            instrument = arguments["instrument"]
            path = arguments["path"]
            start = arguments["start"]
            end = arguments["end"]
            mean_freq = arguments.get("mean_freq", "1h")
            qc = arguments.get("qc", True)
            reset = arguments.get("reset", False)

            # Validate path
            if not Path(path).exists():
                return [TextContent(type="text", text=f"Error: Path does not exist: {path}")]

            df = RawDataReader(
                instrument=instrument,
                path=path,
                start=start,
                end=end,
                mean_freq=mean_freq,
                qc=qc,
                reset=reset
            )

            # Return summary + first/last rows
            result = f"""# {instrument} Data Loaded Successfully

**Time Range**: {df.index.min()} to {df.index.max()}
**Rows**: {len(df):,}
**Columns**: {', '.join(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}

## Summary Statistics
```
{df.describe().to_string()}
```

## First 5 Rows
```
{df.head().to_string()}
```

## Last 5 Rows
```
{df.tail().to_string()}
```
"""
            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error reading data: {str(e)}")]

    elif name == "get_data_summary":
        try:
            from AeroViz import RawDataReader

            df = RawDataReader(
                instrument=arguments["instrument"],
                path=arguments["path"],
                start=arguments["start"],
                end=arguments["end"],
                mean_freq="1h",
                qc=True
            )

            # Calculate comprehensive summary
            summary = {
                "time_range": {
                    "start": str(df.index.min()),
                    "end": str(df.index.max()),
                    "total_hours": len(df)
                },
                "data_completeness": {
                    col: f"{(df[col].notna().sum() / len(df) * 100):.1f}%"
                    for col in df.columns[:10]
                },
                "statistics": df.describe().to_dict()
            }

            return [TextContent(type="text", text=f"```json\n{json.dumps(summary, indent=2, default=str)}\n```")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    elif name == "calculate_optical_properties":
        try:
            from AeroViz.dataProcess.Optical import Optical
            import pandas as pd

            abs_data = json.loads(arguments["absorption_data"])
            df = pd.DataFrame(abs_data)

            result = "# Optical Properties Calculation\n\n"
            result += "Use AeroViz.dataProcess.Optical for:\n"
            result += "- AAE (Absorption Ångström Exponent)\n"
            result += "- SAE (Scattering Ångström Exponent)\n"
            result += "- SSA (Single Scattering Albedo)\n"
            result += "- Mass absorption/scattering coefficients\n"

            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
