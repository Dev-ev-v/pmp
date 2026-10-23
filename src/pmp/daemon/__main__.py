from pmp.paths import paths
from pmp.daemon.daemon import PMPDaemon


def main():
	daemon = PMPDaemon(paths.daemon_pid)
	
	daemon.run()


if __name__ == "__main__":
    main()