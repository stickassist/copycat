import configparser

class Config:
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path
        self.config = configparser.ConfigParser()
        self.read_config()

    def read_config(self):
        try:
            with open(self.config_file_path, 'r') as file:
                self.config.read_file(file)
        except FileNotFoundError:
            print(f"Config file '{self.config_file_path}' not found. Creating a new one.")
            self.write_config()

    def get_sections(self):
        return self.config.sections()
    
    def get_section(self, section):
        return self.config[section]

    def get_setting(self, section, key, default=None):
        try:
            value = self.config.get(section, key)
            
            if value == "True":
                return True
            elif value == "False":
                return False
            elif value.isdigit():
                if value.find(".") != -1:
                    return float(value)
                else:
                    return int(value)
            else:
                return value
            
        except (configparser.NoSectionError, configparser.NoOptionError):
            self.set_setting(section, key, default)
            return default

    def set_setting(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, key, str(value))
        self.write_config()

    def write_config(self):
        with open(self.config_file_path, 'w') as file:
            self.config.write(file)
