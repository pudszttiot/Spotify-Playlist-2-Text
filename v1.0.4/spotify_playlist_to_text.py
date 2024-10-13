import sys
import re
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QVBoxLayout,
    QProgressBar,
    QHBoxLayout,
    QComboBox,
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from PyQt5.Qt import Qt
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import csv

# Spotify API credentials
CLIENT_ID = "84d6cd4d6351419d8dc750a2768930ff"
CLIENT_SECRET = "94ca367fbd01433b8b01923d661c3431"

# Authenticate with the Spotify API
sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )
)


class SpotifyPlaylistApp(QWidget):
    def __init__(self):
        super().__init__()
        # Set up the GUI layout
        self.initUI()

    def initUI(self):
        # Window title and size
        self.setWindowTitle("SP2T")
        self.setGeometry(300, 300, 500, 250)
        self.setWindowIcon(QIcon(r"../Images/SP2T.png"))

        # Load the external QSS stylesheet
        self.load_stylesheet()

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Playlist URL entry
        self.label = QLabel("Enter Spotify Playlist URL:")
        self.label.setFont(QFont("Arial", 20))
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.entry_url = QLineEdit(self)
        self.entry_url.setPlaceholderText("https://open.spotify.com/playlist/...")
        self.entry_url.setFont(QFont("Arial", 10))
        layout.addWidget(self.entry_url)

        # Export format selection
        self.export_format_label = QLabel("Select Export Format:")
        self.export_format_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.export_format_label)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["Text (.txt)", "HTML (.html)", "CSV (.csv)"])
        layout.addWidget(self.format_combo)

        # Process button
        self.process_btn = QPushButton("Process Playlist")
        self.process_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.process_btn.clicked.connect(self.start_playlist_processing)
        layout.addWidget(self.process_btn)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Footer (for additional info or branding)
        footer_layout = QHBoxLayout()
        footer_layout.setAlignment(Qt.AlignRight)

        self.footer_label = QLabel("")
        self.footer_label.setFont(QFont("Arial", 10, QFont.StyleItalic))
        footer_layout.addWidget(self.footer_label)

        layout.addLayout(footer_layout)

        # Apply the layout
        self.setLayout(layout)

    def load_stylesheet(self):
        """Load the QSS stylesheet from an external file."""
        try:
            with open("style.qss", "r") as file:
                stylesheet = file.read()
                self.setStyleSheet(stylesheet)
        except FileNotFoundError:
            print("Style sheet file not found. Proceeding without it.")

    def start_playlist_processing(self):
        """Start the playlist processing in a separate thread to avoid freezing the GUI."""
        playlist_url = self.entry_url.text()

        # Enhanced validation of playlist URL
        if not self.validate_spotify_url(playlist_url):
            QMessageBox.critical(
                self, "Invalid URL", "Please enter a valid Spotify playlist URL."
            )
            return

        # Select file format and set extension
        export_format = self.format_combo.currentText()
        file_types = {
            "Text (.txt)": "Text files (*.txt)",
            "HTML (.html)": "HTML files (*.html)",
            "CSV (.csv)": "CSV files (*.csv)",
        }
        output_file, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", file_types[export_format]
        )

        if not output_file:
            return

        self.playlist_worker = PlaylistWorker(playlist_url, output_file, export_format)
        self.playlist_worker.progress_signal.connect(self.update_progress)
        self.playlist_worker.finished_signal.connect(self.on_playlist_processed)
        self.playlist_worker.start()

    def validate_spotify_url(self, url):
        """Validate the Spotify playlist URL using regex."""
        spotify_url_pattern = re.compile(
            r"https?://open\.spotify\.com/playlist/[A-Za-z0-9]+"
        )
        return bool(spotify_url_pattern.match(url))

    def update_progress(self, progress):
        """Update the progress bar with the current progress."""
        self.progress_bar.setValue(progress)

    def on_playlist_processed(self, success, output_file, tracks_count):
        """Called when the playlist processing is complete."""
        self.progress_bar.setValue(100)
        if success:
            QMessageBox.information(
                self,
                "Success",
                f"Tracks have been saved to '{output_file}'\nTotal tracks processed: {tracks_count}",
            )
        else:
            QMessageBox.critical(
                self, "Error", "Failed to save the tracks to the file."
            )


class PlaylistWorker(QThread):
    """A QThread class to handle the playlist processing in the background."""

    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str, int)

    def __init__(self, playlist_url, output_file, export_format):
        super().__init__()
        self.playlist_url = playlist_url
        self.output_file = output_file
        self.export_format = export_format

    def run(self):
        """Main logic to retrieve the playlist details and save them to a file."""
        playlist_name, tracks = self.get_playlist_details(self.playlist_url)
        if tracks:
            total_tracks = len(tracks)
            if self.export_format == "Text (.txt)":
                success = self.save_tracks_as_text(
                    tracks,
                    self.output_file,
                    self.playlist_url,
                    playlist_name,
                    total_tracks,
                )
            elif self.export_format == "HTML (.html)":
                success = self.save_tracks_as_html(
                    tracks, self.output_file, self.playlist_url, playlist_name
                )
            elif self.export_format == "CSV (.csv)":
                success = self.save_tracks_as_csv(
                    tracks, self.output_file, playlist_name
                )

            self.finished_signal.emit(success, self.output_file, total_tracks)
        else:
            self.finished_signal.emit(False, "", 0)

    def get_playlist_details(self, playlist_url):
        """Retrieve playlist details from Spotify and include the Spotify URL for each track."""
        try:
            playlist_id = playlist_url.split("/")[-1].split("?")[0]
            playlist = sp.playlist(playlist_id)
            playlist_name = playlist["name"]

            # Get playlist tracks (handling pagination)
            tracks = []
            results = sp.playlist_tracks(playlist_id)
            tracks.extend(results["items"])

            while results["next"]:
                results = sp.next(results)
                tracks.extend(results["items"])

            # Extract track details with URL
            track_details = [
                {
                    "artists": ", ".join(
                        artist["name"] for artist in item["track"]["artists"]
                    ),
                    "track_name": item["track"]["name"],
                    "track_url": item["track"]["external_urls"]["spotify"],
                }
                for item in tracks
            ]

            return playlist_name, track_details

        except Exception as e:
            print(f"Error retrieving playlist details: {e}")
            return None, []

    def save_tracks_as_text(
        self, tracks, filename, playlist_url, playlist_name, total_tracks
    ):
        """Save track details to a text file."""
        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(f"Playlist URL: {playlist_url}\n")
                file.write(f"Playlist Name: {playlist_name}\n\n")

                for i, track in enumerate(tracks):
                    file.write(
                        f"{track['artists']} - {track['track_name']} (Spotify URL: {track['track_url']})\n"
                    )
                    progress = int((i + 1) / total_tracks * 100)
                    self.progress_signal.emit(progress)

            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False

    def save_tracks_as_html(self, tracks, filename, playlist_url, playlist_name):
        """Save track details as an HTML file with enhanced styling."""
        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <meta http-equiv="X-UA-Compatible" content="ie=edge">
                    <title>{playlist_name} - Spotify Playlist</title>
                    <style>
                        body {{
                            font-family: 'Arial', sans-serif;
                            background-color: #f4f4f9;
                            color: #333;
                            margin: 0;
                            padding: 0;
                            line-height: 1.6;
                        }}
                        .container {{
                            max-width: 800px;
                            margin: 30px auto;
                            padding: 20px;
                            border: 1px solid #ccc;
                            border-radius: 5px;
                            background-color: #fff;
                        }}
                        h1 {{
                            text-align: center;
                            color: #2c3e50;
                        }}
                        h3 {{
                            text-align: center;
                            color: #555;
                        }}
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                            margin-top: 20px;
                        }}
                        th, td {{
                            padding: 10px;
                            text-align: left;
                            border-bottom: 1px solid #ddd;
                        }}
                        th {{
                            background-color: #007bff;
                            color: white;
                        }}
                        tr:hover {{
                            background-color: #f1f1f1;
                        }}
                        a {{
                            color: #007bff;
                            text-decoration: none;
                        }}
                        a:hover {{
                            text-decoration: underline;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>{playlist_name}</h1>
                        <h3>Playlist URL: <a href="{playlist_url}" target="_blank">{playlist_url}</a></h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Artist(s)</th>
                                    <th>Track Name</th>
                                    <th>Spotify URL</th>
                                </tr>
                            </thead>
                            <tbody>
                """)

                for track in tracks:
                    file.write(f"""
                        <tr>
                            <td>{track['artists']}</td>
                            <td>{track['track_name']}</td>
                            <td><a href="{track['track_url']}" target="_blank">Listen</a></td>
                        </tr>
                    """)

                file.write("""
                            </tbody>
                        </table>
                    </div>
                </body>
                </html>
                """)
            return True
        except Exception as e:
            print(f"Error saving to HTML file: {e}")
            return False

    def save_tracks_as_csv(self, tracks, filename, playlist_name):
        """Save track details as a CSV file with headers."""
        try:
            with open(filename, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(
                    ["Playlist Name", "Artist", "Track Name", "Spotify URL"]
                )
                for track in tracks:
                    writer.writerow(
                        [
                            playlist_name,
                            track["artists"],
                            track["track_name"],
                            track["track_url"],
                        ]
                    )

            return True
        except Exception as e:
            print(f"Error saving to CSV file: {e}")
            return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpotifyPlaylistApp()
    window.show()
    sys.exit(app.exec_())
