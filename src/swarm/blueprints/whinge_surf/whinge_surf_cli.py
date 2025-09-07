import argparse
import sys

from swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSurfBlueprint


def main():
    parser = argparse.ArgumentParser(description="whinge-surf: background subprocess butler & self-updater")
    parser.add_argument('--run', nargs='+', help='Run a subprocess in the background (supply command as args)')
    parser.add_argument('--status', type=int, help='Check status of a subprocess by PID')
    parser.add_argument('--output', type=int, help='Get output from a subprocess by PID')
    parser.add_argument('--kill', type=int, help='Kill/cancel a subprocess by PID')
    parser.add_argument('--self-update', type=str, help='Prompt to update whinge-surf code (self-improvement)')
    parser.add_argument('--no-test', action='store_true', help='Skip running tests after self-update')
    parser.add_argument('--analyze-self', action='store_true', help='Analyze whinge-surf source code and print summary')
    parser.add_argument('--analyze-output', choices=['ansi', 'text', 'json'], default='ansi', help='Output format for analysis')
    parser.add_argument('--list-jobs', action='store_true', help='List all subprocess jobs')
    parser.add_argument('--show-output', type=int, help='Show output of a subprocess by PID')
    parser.add_argument('--tail', type=int, help='Tail live output of a subprocess by PID')
    parser.add_argument('--resource-usage', type=int, help='Show resource usage for a subprocess by PID')
    parser.add_argument('--prune-jobs', action='store_true', help='Remove finished jobs from the job table')
    args = parser.parse_args()

    ws = WhingeSurfBlueprint()

    if args.run:
        # If a single string is passed, treat it as a shell command
        cmd = ["/bin/sh", "-c", args.run[0]] if len(args.run) == 1 else args.run
        pid = ws.run_subprocess_in_background(cmd)
        print(ws.ux.ansi_emoji_box(
            "Subprocess Started",
            f"PID: {pid}\nCommand: {' '.join(cmd)}",
            op_type="run",
            params={'cmd': cmd},
        ))
        return
    if args.status is not None:
        status = ws.check_subprocess_status(args.status)
        print(ws.ux.ansi_emoji_box(
            "Subprocess Status",
            str(status) if status else f"No such PID: {args.status}",
            op_type="status",
            params={'pid': args.status},
        ))
        return
    if args.output is not None:
        output = ws.get_subprocess_output(args.output)
        print(ws.ux.ansi_emoji_box(
            "Subprocess Output",
            output if output is not None else f"No such PID: {args.output}",
            op_type="output",
            params={'pid': args.output},
        ))
        return
    if args.kill is not None:
        result = ws.kill_subprocess(args.kill)
        print(ws.ux.ansi_emoji_box(
            "Subprocess Kill",
            result,
            op_type="kill",
            params={'pid': args.kill},
        ))
        return
    if args.list_jobs:
        print(ws.list_jobs())
        return
    if args.show_output is not None:
        print(ws.show_output(args.show_output))
        return
    if args.tail is not None:
        ws.tail_output(args.tail)
        return
    if args.resource_usage is not None:
        print(ws.resource_usage(args.resource_usage))
        return
    if args.analyze_self:
        print(ws.analyze_self(output_format=args.analyze_output))
        return
    if args.prune_jobs:
        print(ws.prune_jobs())
        return
    if args.self_update:
        result = ws.self_update_from_prompt(args.self_update, test=not args.no_test)
        print(result)
        return
    parser.print_help()

if __name__ == "__main__":
    import sys
    if sys.argv[0].endswith("whinge_surf_cli.py") or sys.argv[0].endswith("whinge_surf_cli"):  # legacy
        print("[INFO] For future use, invoke this CLI as 'whinge' instead of 'whinge_surf_cli'.")
        main()
    elif sys.argv[0].endswith("whinge"):  # preferred new name
        main()
    else:
        main()
