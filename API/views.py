import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import urllib.request
import re, os, time


def text_finder(url, dirpath):
    print("Start text scraping")
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    html_page = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(html_page, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    texts = soup.findAll(text=True)
    text_data = u" ".join(t.strip() for t in texts)
    print(text_data)

    if text_data:
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
    else:
        return False

    with open(os.path.join(dirpath, "SiteText.txt"), "w", encoding='utf-8') as text_file:
        text_file.write(text_data)
    return True


def picture_finder(site, dirpath):
    print("Start pictures scraping")
    response = requests.get(site)
    soup = BeautifulSoup(response.text, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    img_tags = soup.find_all('img', {"src": True})
    urls = [img['src'] for img in img_tags]
    # print(f"All urls: {urls}", "\n")
    if urls:
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
    else:
        return False
    
    for url in urls:
        if 'http' not in url:
            url = '{}{}'.format(site, url)
        print(url)
        if not re.search(r'/([\w,_-]+[.](jpg|gif|png))', url) is None:
            picture_name = re.search(r'/([\w,_-]+[.](jpg|gif|png))', url).group(0).replace("/", "")
            print(f"Filename: {picture_name}, url: {url}")
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(url, os.path.join(dirpath, picture_name))
    return True


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
        print(dir_path)

        if request.data["type"] == "pictures":
            if picture_finder(request.data["url"], dir_path):
                return Response(data={"Success": "Done"}, status=status.HTTP_200_OK)
            else:
                return Response(data={"Error": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif request.data["type"] == "text":
            if text_finder(request.data["url"], dir_path):
                return Response(data={"Success": "Done"}, status=status.HTTP_200_OK)
            else:
                return Response(data={"Error": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif request.data["type"] == "both":
            if (picture_finder(request.data["url"], dir_path) and text_finder(request.data["url"], dir_path)):
                return Response(data={"Success": "Done"}, status=status.HTTP_200_OK)
            else:
                return Response(data={"Error": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
