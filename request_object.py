

class requestObject:
    url = ''
    status_code = 0
    content = ''

    def __init__(self, url, status_code, content):
        self.url = url
        self.status_code = status_code
        self.content = content

    def __str__(self):
        return "<Response [{}]>".format(self.status_code)

    def __repr__(self):
        return "<Response [{}]>".format(self.status_code)

