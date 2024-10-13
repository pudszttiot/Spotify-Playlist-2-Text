import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QMessageBox, QFileDialog, QVBoxLayout
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
        self.setWindowTitle('Spotify Playlist to Text')
        self.setGeometry(300, 300, 400, 150)

        layout = QVBoxLayout()

        # Playlist URL entry
        self.label = QLabel('Spotify Playlist URL:')
        layout.addWidget(self.label)

        self.entry_url = QLineEdit(self)
        layout.addWidget(self.entry_url)

        # Process button
        self.process_btn = QPushButton('Process Playlist', self)
        self.process_btn.clicked.connect(self.process_playlist)
        layout.addWidget(self.process_btn)

        # Set the layout for the QWidget
        self.setLayout(layout)

    def process_playlist(self):
        """
        Process the Spotify playlist URL entered by the user.
        """
        playlist_url = self.entry_url.text()
        if not playlist_url.startswith("https://open.spotify.com/playlist/"):
            QMessageBox.critical(self, 'Invalid URL', 'Please enter a valid Spotify playlist URL.')
            return

        output_file, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text files (*.txt)")
        if not output_file:
            return

        playlist_name, tracks = self.get_playlist_details(playlist_url)
        if tracks:
            if self.save_tracks_to_file(tracks, output_file, playlist_url, playlist_name):
                QMessageBox.information(self, 'Success', f"Tracks have been saved to '{output_file}'\nTotal tracks processed: {len(tracks)}")
            else:
                QMessageBox.critical(self, 'Error', 'Failed to save the tracks to the file.')
        else:
            QMessageBox.critical(self, 'Error', 'No tracks were found or an error occurred.')

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


    def save_tracks_to_file(self, tracks, filename, playlist_url, playlist_name):
        """
        Save track details to a text file.
        """
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(f"Playlist URL: {playlist_url}\n")
                file.write(f"Playlist Name: {playlist_name}\n\n")
                file.writelines(f"{track}\n" for track in tracks)
            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SpotifyPlaylistApp()
    ex.show()
    sys.exit(app.exec_())
