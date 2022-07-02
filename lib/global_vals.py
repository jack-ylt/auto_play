
class EmulatorNotFound(Exception):
    pass

class EmulatorStartupTimeout(Exception):
    pass

class GameNotFound(Exception):
    pass

class UnsupportGame(Exception):
    pass

class LoginTimeout(Exception):
    pass

class RestartTooMany(Exception):
    pass

class UserConfigError(Exception):
    pass
