class IssueStatusNotFoundException(Exception):
    def __init__(self, status_name: str):
        self.status_name = status_name

    def __str__(self):
        return f"No issue status with the name \"{self.status_name}\" could be found. Please check your config.yaml."
