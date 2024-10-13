import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, QMessageBox, QFileDialog, QVBoxLayout, QProgressBar, QHBoxLayout)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from PyQt5.Qt import Qt

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Spotify API credentials
CLIENT_ID = '84d6cd4d6351419d8dc750a2768930ff'
CLIENT_SECRET = '94ca367fbd01433b8b01923d661c3431'

# Authenticate with the Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))


class SpotifyPlaylistApp(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the GUI layout
        self.initUI()

    def initUI(self):
        # Window title and size
        self.setWindowTitle('Spotify Playlist to Text')
        self.setGeometry(300, 300, 480, 220)
        self.setWindowIcon(QIcon(r"../Images/SP2T.png"))

        # Load the external QSS stylesheet
        self.load_stylesheet()

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Playlist URL entry
        self.label = QLabel('Enter Spotify Playlist URL:')
        self.label.setFont(QFont("Arial", 12))
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.entry_url = QLineEdit(self)
        self.entry_url.setPlaceholderText("https://open.spotify.com/playlist/...")
        self.entry_url.setFont(QFont("Arial", 10))
        layout.addWidget(self.entry_url)

        # Process button
        self.process_btn = QPushButton('Process Playlist')
        self.process_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.process_btn.clicked.connect(self.start_playlist_processing)
        layout.addWidget(self.process_btn)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)  # Set maximum value for progress bar
        self.progress_bar.setTextVisible(True)  # Show progress text
        layout.addWidget(self.progress_bar)

        # Footer (for additional info or branding)
        footer_layout = QHBoxLayout()
        footer_layout.setAlignment(Qt.AlignRight)

        self.footer_label = QLabel("Powered by Spotify API")
        self.footer_label.setFont(QFont("Arial", 10, QFont.StyleItalic))
        footer_layout.addWidget(self.footer_label)

        layout.addLayout(footer_layout)

        # Apply the layout
        self.setLayout(layout)

    def load_stylesheet(self):
        """
        Load the QSS stylesheet from an external file.
        """
        with open("style.qss", "r") as file:
            stylesheet = file.read()
            self.setStyleSheet(stylesheet)

    def start_playlist_processing(self):
        """
        Start the playlist processing in a separate thread to avoid freezing the GUI.
        """
        playlist_url = self.entry_url.text()
        if not playlist_url.startswith("https://open.spotify.com/playlist/"):
            QMessageBox.critical(self, 'Invalid URL', 'Please enter a valid Spotify playlist URL.')
            return

        output_file, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text files (*.txt)")
        if not output_file:
            return

        self.playlist_worker = PlaylistWorker(playlist_url, output_file)
        self.playlist_worker.progress_signal.connect(self.update_progress)
        self.playlist_worker.finished_signal.connect(self.on_playlist_processed)
        self.playlist_worker.start()

    def update_progress(self, progress):
        """
        Update the progress bar with the current progress.
        """
        self.progress_bar.setValue(progress)

    def on_playlist_processed(self, success, output_file, tracks_count):
        """
        Called when the playlist processing is complete.
        """
        self.progress_bar.setValue(100)  # Ensure progress bar is full when finished
        if success:
            QMessageBox.information(self, 'Success', f"Tracks have been saved to '{output_file}'\nTotal tracks processed: {tracks_count}")
        else:
            QMessageBox.critical(self, 'Error', 'Failed to save the tracks to the file.')


class PlaylistWorker(QThread):
    """
    A QThread class to handle the playlist processing in the background.
    """
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str, int)

    def __init__(self, playlist_url, output_file):
        super().__init__()
        self.playlist_url = playlist_url
        self.output_file = output_file

    def run(self):
        """
        Main logic to retrieve the playlist details and save them to a file.
        """
        playlist_name, tracks = self.get_playlist_details(self.playlist_url)
        if tracks:
            # Set total tracks count for progress calculation
            total_tracks = len(tracks)
            success = self.save_tracks_to_file(tracks, self.output_file, self.playlist_url, playlist_name, total_tracks)
            self.finished_signal.emit(success, self.output_file, total_tracks)
        else:
            self.finished_signal.emit(False, "", 0)

    def get_playlist_details(self, playlist_url):
        """
        Retrieve playlist details from Spotify and include the Spotify URL for each track.
        """
        try:
            playlist_id = playlist_url.split("/")[-1].split("?")[0]
            playlist = sp.playlist(playlist_id)
            playlist_name = playlist['name']

            # Get playlist tracks (handling pagination)
            tracks = []
            results = sp.playlist_tracks(playlist_id)
            tracks.extend(results['items'])

            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])

            # Extract track details with URL
            track_details = [
                f"{', '.join(artist['name'] for artist in item['track']['artists'])} - {item['track']['name']} "
                f"(Spotify URL: {item['track']['external_urls']['spotify']})"
                for item in tracks
            ]

            return playlist_name, track_details

        except Exception as e:
            print(f"Error retrieving playlist details: {e}")
            return None, []

    def save_tracks_to_file(self, tracks, filename, playlist_url, playlist_name, total_tracks):
        """
        Save track details to a text file.
        """
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(f"Playlist URL: {playlist_url}\n")
                file.write(f"Playlist Name: {playlist_name}\n\n")
                
                for i, track in enumerate(tracks):
                    file.write(f"{track}\n")
                    # Emit progress as a percentage
                    progress = int((i + 1) / total_tracks * 100)
                    self.progress_signal.emit(progress)

            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SpotifyPlaylistApp()
    ex.show()
    sys.exit(app.exec_())
