class MPVError(Exception):
    """Erro genérico do player mpv."""
    pass


class MPVConnectionError(MPVError):
    """Não foi possível conectar ao mpv."""
    pass


class MPVCommandError(MPVError):
    """O mpv recusou ou falhou ao executar um comando."""
    pass