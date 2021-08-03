class ScriptException(Exception):
    def __init__(self, err_code: str, err_str: str, parent_exc: Exception = None) -> None:
        """
        Script exception. Prepared for pretty error printing.

        :param err_code: Unique code for the experienced error
        :param err_str: String describing the error
        :param parent_exc: Parent exception, if any
        """
        super().__init__(f"{err_code}: {err_str}")
        self.err_code = err_code
        self.err_str = err_str
        self.parent_exc = parent_exc