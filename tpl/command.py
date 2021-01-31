
class TPLcommand():
    def __init__(self, params, command_line, control_id, execute_flag, application, tpl):
        self.params = params
        self.command_line = command_line
        self.control_id = control_id
        self.execute_flag = execute_flag
        self.application = application
        self.tpl = tpl

    def execute(self):
        print("execute")
