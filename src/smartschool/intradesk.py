import os
from functools import cached_property
from .session import SessionMixin

class ItemNotFoundError(Exception):
    def __init__(self, filename, current_folder):
        super().__init__(f'No item {filename} in {current_folder}')

class Folder(SessionMixin):
    '''Represents a folder in the intradesk'''
    def __init__(self, session: Smartschool, id: str, parent: Folder, platformId: str, name: str):
        super().__init__(session)
        self.id = id
        self.parent = parent
        self.platformId = platformId
        self.name = name

    @cached_property
    def items(self):
        '''list of items in this folder'''
        loc = f'/intradesk/api/v1/{self.platformId}/directory-listing/forTreeOnlyFolders/{self.id}'
        folders, files, weblinks = self.session.json(loc, method = 'get').values() # weblinks is not used

        ls = []
        
        for fo in folders:
            ls.append(Folder(self.session, fo['id'], self, fo['platform']['id'], fo['name']))

        for fi in files:
            ls.append(File(self.session, fi['id'], self, fi['platform']['id'], fi['name']))     
        
        return ls

    def get_item(self, item_name: str):
        '''Gets an item in this folder by its name'''
        for it in self.items:
            if it.name == item_name:
                return it
        raise ItemNotFoundError(item_name, self.name)

    def __repr__(self):
        return 'Folder: ' + self.name

    def upload(self, filename, mime_type):
        '''Uploads a local file in this folder'''
        # to do: infer the mime type automatically
        
        # 1. get an temporary uplaod directory
        uploadDir = self.session.json('/upload/api/v1/get-upload-directory', method = 'get')['uploadDir']

        # 2. upload the file to this temporary upload directory
        url = "Upload/Upload/Index"
        data = {"uploadDir": uploadDir}
        files = {"file": (filename, open(filename, "rb"), mime_type)}
        response1 = self.session.request('POST', url, files = files, data = data)

        # 3. move the uplaoded file to the intradesk directory
        url = f'intradesk/api/v1/{self.platformId}/files/upload'
        payload = {"parentFolderId": self.id, 'uploadDir': uploadDir}
        response2 = self.session.request('POST', url, json = payload)

        if not (response1.status_code == 200 and response2.status_code == 201):
            print('Error in uploading')

        return response1, response2    

class File(SessionMixin):
    '''Represents a file in the intradesk'''
    def __init__(self, session: Smartschool, id: str, parent: Folder, platformId: str, name: str):
        super().__init__(session)
        self.id = id
        self.parent = parent
        self.platformId = platformId
        self.name = name

        splitted_name = name.split('.')
        if len(splitted_name) == 1:
            self.suffix = ''
        else:
            self.suffix = f'.{splitted_name[-1]}'

    def __repr__(self):
        return 'File: ' + self.name
        
    def download(self, directory = None):
        '''download this file locally to directory'''
        r = self.session.request('GET', f'/intradesk/api/v1/{self.platformId}/files/{self.id}/download')

        # ensure the file does not exist yet in the directory
        download_name = self.name
        n = 0
        while download_name in os.listdir(directory):
            n += 1
            download_name = self.name[: - len(self.suffix)] + f'({n})' + self.suffix

        download_path = f'{directory}/' if directory is not None else '' 
        
        with open(f'{download_path}{download_name}', 'wb') as f:
            f.write(r.content)

class Intradesk(Folder):
    '''Root folder of the intradesk'''
    def __init__(self, session: Smartschool):
        platformId = session.json("/Topnav/getCourseConfig", method="post")["own"][0]['platformId']
        id = ''
        parent = None
        name = 'intradesk'
        super().__init__(session, id, parent, platformId, name)