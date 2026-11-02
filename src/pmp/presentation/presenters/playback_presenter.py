class PlaybackPresenter:
    def __init__(self, renderer):
    	self._renderer = renderer
    	
    def show_state(self, state):
        print(self._renderer.render_state(state))
        
    def show_queue(self, queue, playlist_index):
        print(self._renderer.render_queue(queue, playlist_index))
        
    def show_library(self, playlists, root_songs, scan_errors):
        print(self._renderer.render_library(playlists, root_songs, scan_errors))
        		
    def show_stats(self, stats, get_song_by_path, short):
        print(self._renderer.render_stats(stats, get_song_by_path, short))