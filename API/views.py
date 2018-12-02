import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import urllib.request
import re, os, time
from background_task import background
from background_task.models import Task
from background_task.models_completed import CompletedTask


@background()
def text_finder(site, dirpath):
    print(f"Start text scraping for {site}")
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    html_page = urllib.request.urlopen(site).read()
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

    print(f"Finished text scraping for {site}")


@background()
def picture_finder(site, dirpath):
    print(f"Start pictures scraping from {site}")
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

    print(f"Finished pictures scraping from {site}")


class ScrapperView(APIView):

    def post(self, request):
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
            verbose_name = picture_finder(request.data["url"], dir_path, verbose_name=time.time())
            new_task = Task.objects.get(verbose_name=verbose_name)
            task_hash = new_task.task_hash
            return Response(data={"success": "done", "task_hash": task_hash}, status=status.HTTP_200_OK)
        elif request.data["type"] == "text":
            verbose_name = text_finder(request.data["url"], dir_path, verbose_name=time.time())
            new_task = Task.objects.get(verbose_name=verbose_name)
            task_hash = new_task.task_hash
            return Response(data={"success": "done", "task_hash": task_hash}, status=status.HTTP_200_OK)
        elif request.data["type"] == "both":
            verbose_name_pictures = picture_finder(request.data["url"], dir_path, verbose_name=time.time())
            new_task = Task.objects.get(verbose_name=verbose_name_pictures)
            task_hash_pictures = new_task.task_hash
            verbose_name_text = text_finder(request.data["url"], dir_path, verbose_name=time.time())
            new_task = Task.objects.get(verbose_name=verbose_name_text)
            task_hash_text = new_task.task_hash
            return Response(data={"success": "done", "task_hash_text": task_hash_text, "task_hash_pictures": task_hash_pictures}, status=status.HTTP_200_OK)

    def get(self, request):
        task_hash = request.data["hash"]
        if Task.objects.filter(task_hash=task_hash).count() == 1 and not CompletedTask.objects.filter(task_hash=task_hash).exists():
            unfinished_task = CompletedTask.objects.get(task_hash=task_hash)
            return Response(data={"task_hash": task_hash, "state": "working", "id": unfinished_task.id}, status=status.HTTP_200_OK)
        elif not Task.objects.filter(task_hash=task_hash).exists() and CompletedTask.objects.filter(task_hash=task_hash).count() == 1:
            finished_task = CompletedTask.objects.get(task_hash=task_hash)
            return Response(data={"task_hash": task_hash, "state": "finished", "id": finished_task.id}, status=status.HTTP_200_OK)
        else:
            return Response(data={"task_hash": task_hash, "state": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
