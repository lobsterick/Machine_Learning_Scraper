import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import urllib.request
import re, os, time
from background_task import background

tasks = {}


@background()
def text_finder(url, dirpath, task_id):
    global tasks
    task_id = int(task_id)

    tasks[task_id] = "started"
    print("Start text scraping, id: ", task_id)

    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    html_page = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(html_page, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    texts = soup.findAll(text=True)
    text_data = u" ".join(t.strip() for t in texts)

    if text_data:
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

    with open(os.path.join(dirpath, "SiteText.txt"), "w", encoding='utf-8') as text_file:
        text_file.write(text_data)

    tasks[task_id] = "finished"
    print("Finished text scraping, id: ", task_id)


@background()
def picture_finder(site, dirpath, task_id):
    global tasks
    task_id = int(task_id)
    tasks[task_id] = "started"
    print("Start pictures scraping, id: ", task_id)
    response = requests.get(site)
    soup = BeautifulSoup(response.text, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    img_tags = soup.find_all('img', {"src": True})
    urls = [img['src'] for img in img_tags]
    if urls:
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

    for url in urls:
        if 'http' not in url:
            url = '{}{}'.format(site, url)
        if not re.search(r'/([\w,_-]+[.](jpg|gif|png))', url) is None:
            picture_name = re.search(r'/([\w,_-]+[.](jpg|gif|png))', url).group(0).replace("/", "")
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(url, os.path.join(dirpath, picture_name))

    tasks[task_id] = "finished"
    print("Finished pictures scraping, id: ", task_id)


class ScrapperView(APIView):

    def post(self, request):
        global tasks
        if not (request.data.get("type") and request.data.get("url")):
            return Response(data={"Error": "Didn't provide type or url of request)"}, status=status.HTTP_400_BAD_REQUEST)
        elif not request.data["type"] in ["pictures", "text", "both"]:
            return Response(data={"Error": "You must choose type of request as pictures, text or both)"}, status=status.HTTP_400_BAD_REQUEST)

        url = request.data["url"]
        response = requests.get(url)
        if not response.status_code == requests.codes.ok:
            return Response(data={"Error": "Url didn't respond properly"}, status=status.HTTP_404_NOT_FOUND)

        if not os.path.exists("scrapped-data"):
            os.makedirs("scrapped-data")

        today_day_str = time.strftime("%Y.%m.%d")
        today_hour_str = time.strftime("%H.%M.%S")
        dir_path = os.path.join('scrapped-data', today_day_str, today_hour_str)

        if request.data["type"] == "pictures":
            task_id = len(tasks)
            tasks.update({task_id: "undone"})
            picture_finder(request.data["url"], dir_path, task_id)
            return Response(data={"success": "done", "task_id": task_id}, status=status.HTTP_200_OK)
        elif request.data["type"] == "text":
            task_id = len(tasks)
            tasks.update({task_id: "undone"})
            text_finder(request.data["url"], dir_path, task_id)
            return Response(data={"success": "done", "task_id": task_id}, status=status.HTTP_200_OK)
        elif request.data["type"] == "both":
            task_id = len(tasks)
            tasks.update({task_id: "undone"})
            text_finder(request.data["url"], dir_path, task_id)
            task_id = len(tasks)
            tasks.update({task_id: "undone"})
            picture_finder(request.data["url"], dir_path, task_id)
            return Response(data={"success": "done", "task_id_text": task_id - 1, "task_id_pictures": task_id}, status=status.HTTP_200_OK)

    def get(self, request):
        global tasks
        print(tasks)
        task_id = int(request.data["id"])
        state = tasks[task_id]
        return Response(data={"task_number": task_id, "state": state}, status=status.HTTP_200_OK)
