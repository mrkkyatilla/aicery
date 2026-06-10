# Custom plugins (PLUGIN_PATHS)

Load domain-specific tools and agents from outside the core package.

## Enable

```bash
export PLUGIN_PATHS=examples/stock-advisor
make up
```

Multiple paths (comma-separated):

```bash
export PLUGIN_PATHS=examples/stock-advisor,examples/my-app
```

## Layout

```txt
examples/stock-advisor/
  tools/*.py          # @tool handlers
  agents/*.yaml       # plugin agent manifests
  agents/graph.py     # register_plugin_agent(...)
  data/               # demo fixtures (read via jail_path)
```

## StockPilot example

```bash
export PLUGIN_PATHS=examples/stock-advisor
export USE_MOCK_PROVIDER=true
export HITL_ENABLED=false
bash examples/stock-advisor/scripts/demo.sh
```

Loader: `tools/tools/registry/plugin_loader.py`  
Bootstrap: `runtime/runtime/services/plugin_bootstrap.py`

## Related

- [Tools](tools.md)
- [examples/stock-advisor](../examples/stock-advisor/README.md)
