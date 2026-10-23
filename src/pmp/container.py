### CLI
from pmp.cli.selector import Selector

### PRESENTATION
from pmp.presentation.renderer import PlaybackRenderer
from pmp.presentation.presenters.playback_presenter import PlaybackPresenter

### STORAGE
from pmp.storage.session_store import SessionStore
from pmp.storage.config_store import ConfigStore
from pmp.storage.stats_store import StatsStore

### PLAYBACK
from pmp.player.player import Player
from pmp.playback.playback import PlaybackService
from pmp.playback.runtime import PlaybackRuntime

### LIBRARY
from pmp.library.library import MusicLibrary
from pmp.library.search import SearchEngine

### USER
from pmp.config import Config
from pmp.paths import paths

class Container:

    def __init__(self):

        self.session_store = SessionStore(paths.session)
        
        self.user_config_store = ConfigStore(paths.config)
        
        self.user_config = self.user_config_store.load()
        
        self.config = Config(
        	music_dir=self.user_config.music_dir,
        	socket_path=paths.socket,
        )
        
        self.stats_store = StatsStore(paths.stats)
        
        self.library = MusicLibrary(
            self.config
        )

        self.player = Player(
            self.config
        )
        
        self.selector = Selector()
        
        self.renderer = PlaybackRenderer()
        
        self.presenter = PlaybackPresenter(self.renderer)
        
        self.search = SearchEngine(self.library)
        
        self.playback = PlaybackService(
            self.library,
            self.player,
            self.search,
            self.session_store,
            self.user_config_store,
            self.stats_store,
            PlaybackRuntime.STATS_SAMPLE_INTERVAL,
        )
        
        self.runtime = PlaybackRuntime(self.playback)


container = Container()