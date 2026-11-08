"""Run the shared volatile CEMS service; PLC requires an explicit safe cutover."""
import argparse
import ipaddress
import logging
import resource
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Shared volatile CEMS service')
    parser.add_argument('--source', choices=['simulation', 'plc'], required=True)
    parser.add_argument('--port', type=int, default=8013)
    parser.add_argument('--plc-host')
    parser.add_argument('--plc-port', type=int, default=502)
    parser.add_argument('--plc-unit', type=int, default=1)
    parser.add_argument('--registry', default=str(Path(__file__).resolve().parents[2] / 'registry' / 'cems-parameters.yaml'))
    parser.add_argument('--confirm-exclusive-reader', action='store_true')
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error('port must be 1024..65535')
    if args.source == 'plc':
        if not args.confirm_exclusive_reader or not args.plc_host:
            parser.error('PLC mode requires explicit source identity and confirmed single-reader cutover')
        try:
            ipaddress.ip_address(args.plc_host)
        except ValueError:
            parser.error('PLC host must be the verified numeric address')
        from src.live.activation import ensure_legacy_stopped
        try:
            ensure_legacy_stopped()
        except (RuntimeError, OSError) as error:
            parser.error(str(error))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    logging.disable(logging.CRITICAL)
    import uvicorn
    from src.config import CemsConfig
    from src.live.api import create_app
    from src.live.cache import RollingCache
    from src.live.collector import LiveCollector, ReadOnlyPlcSource, SimulatedSource
    from src.services.registry import load_registry
    registry = load_registry(CemsConfig(parameter_registry_path=args.registry))
    specs = [p for p in registry.parameters if p.stack_id == '1' and p.collect_enabled]
    stack = next(s for s in registry.stacks if s.stack_id == '1')
    source = (ReadOnlyPlcSource(args.plc_host, args.plc_port, args.plc_unit)
              if args.source == 'plc' else SimulatedSource())
    cache = RollingCache(specs, source_mode=source.source_mode)
    collector = LiveCollector(cache, source, stack)
    uvicorn.run(create_app(cache=cache, collector=collector), host='127.0.0.1', port=args.port,
                workers=1, access_log=False, log_config=None, limit_concurrency=16,
                timeout_keep_alive=2)


if __name__ == '__main__':
    main()
