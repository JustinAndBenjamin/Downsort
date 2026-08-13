import sorter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# 1. Header ausgeben
console.print(
    Panel.fit(
        "[bold cyan]📦 DOWNLOADS AUTO-SORTER[/bold cyan]\n[dim]Ordnung im System[/dim]",
        border_style="cyan",
    )
)

# 2. Pfade definieren
download_folder = r"C:\Users\Friedrich\Downloads"

image_folder = r"C:\Users\Friedrich\Downloads\Bilder"
document_folder = r"C:\Users\Friedrich\Downloads\Dokumente"
music_folder = r"C:\Users\Friedrich\Downloads\Musik"
video_folder = r"C:\Users\Friedrich\Downloads\Videos"
application_folder = r"C:\Users\Friedrich\Downloads\Anwendungen"

# 3. Sortiervorgang durchführen
with console.status(
    "[bold green]Sortiere Dateien...[/bold green]", spinner="dots"
):
    moved_files = sorter.sort_downloads(
        download_folder,
        image_folder,
        document_folder,
        music_folder,
        video_folder,
        application_folder,
    )

# 4. Ergebnisse in einer Tabelle anzeigen
if moved_files:
    table = Table(
        title="Verschobene Dateien", title_style="bold yellow", show_header=True
    )
    table.add_column("Dateiname", style="bold white")
    table.add_column("Kategorie", style="bold green")
    table.add_column("Größe", style="cyan", justify="right")

    for file_info in moved_files:
        table.add_row(file_info["name"], file_info["category"], file_info["size"])

    console.print(table)
    console.print(
        f"\n[bold green]✓ Fertig![/bold green] Es wurden [bold yellow]{len(moved_files)}[/bold yellow] Datei(en) einsortiert.\n"
    )
else:
    console.print("[yellow]Keine neuen Dateien zum Sortieren gefunden.[/yellow]\n")

# 5. Fenster offen halten
input("Drücke die Eingabetaste (Enter), um das Fenster zu schließen...")