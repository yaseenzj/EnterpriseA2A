import httpx
import sys
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

def main():
    # First get token
    try:
        r1 = httpx.get("http://127.0.0.1:9006/api/v1/auth/token")
        r1.raise_for_status()
        token = r1.json()["access_token"]
    except Exception as e:
        console.print(f"[red]Failed to get token: {e}[/red]")
        sys.exit(1)

    console.print("\n[bold blue]Sending Natural Language Request to Orchestrator...[/bold blue]\n")
    
    try:
        custom_thread = sys.argv[1] if len(sys.argv) > 1 else None
        
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "request_text": "What is the rules for the booking conference room.. Book a conference room for 2 hours tomorrow and order 5 premium lunches"
        }
        if custom_thread:
            payload["thread_id"] = custom_thread
            console.print(f"[yellow]Using custom Thread ID:[/yellow] {custom_thread}")
            
        r2 = httpx.post("http://127.0.0.1:9006/api/v1/orchestrate", json=payload, headers=headers, timeout=30.0)
        
        data = r2.json()
        
        console.print(Panel.fit(
            f"[bold green]Workflow Status:[/bold green] {data.get('status')}\n"
            f"[bold green]Message:[/bold green] {data.get('response', {}).get('message')}",
            title="[bold white]ORCHESTRATION COMPLETE[/bold white]",
            border_style="green"
        ))
        

        console.print("\n[bold magenta]--- INDIVIDUAL AGENT RESULTS ---[/bold magenta]")
        results = data.get("response", {}).get("results", {})
        
        for task_id, task_data in results.items():
            action = task_data.pop("action", "Unknown")
            
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Key", style="cyan", justify="right")
            table.add_column("Value", style="white")
            
            for key, value in task_data.items():
                if key != "status":
                    if isinstance(value, dict):
                        # Extract the inner answer or format nicely to preserve real linebreaks
                        if "answer" in value:
                            formatted_val = str(value["answer"])
                        else:
                            formatted_val = "\n".join([f"{k}: {v}" for k, v in value.items()])
                    else:
                        formatted_val = str(value)
                        
                    table.add_row(f"{key.replace('_', ' ').title()}:", formatted_val)
                    
            console.print(Panel(
                table,
                title=f"[bold]{task_id.upper()}[/bold] -> [italic yellow]{action}[/italic yellow]",
                title_align="left",
                border_style="blue"
            ))
            
        console.print("\n")
        
    except Exception as e:
        console.print(f"[bold red]Failed to execute: {e}[/bold red]")
        if 'r2' in locals():
            console.print(r2.text)

if __name__ == "__main__":
    main()
