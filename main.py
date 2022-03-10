import traceback
import fastapi
import re, aiohttp, asyncio
import json, time
from bs4 import BeautifulSoup


async def fetch_url(url):
    try:
        starttime = time.time()
        session = aiohttp.ClientSession()
        article = await (await session.get(url)).text()

        article = re.sub(
            r'"Product_image": "([0-9]*)',
            r'"Product_image": "https://static.toiimg.com/photo/\g<1>.cms',
            article,
        )

        article = re.sub(
            r'"url":  "([0-9]*)', r'"url":  "https://www.gadgetsnow.com\g<1>', article
        )

        data = json.loads(article)

        if len(data) > 0:
            results = []
            async def extract_results(i):
                i.update(
                    (
                        await (
                            await session.get(
                                f"https://www.gadgetsnow.com/pwafeeds/gnow/web/show/gadgets/json?uName={i['url'].split('/')[-1]}&url={i['url'].split('https://www.gadgetsnow.com')[1]}"
                            )
                        ).json()
                    )
                    .get("jsonFeed")
                    .get("data")
                    .get("item")
                )
                if i.get("review"):
                    i.pop("review")
                if i.get("reviews"):
                    i.pop("reviews")
                if i.get("userReview"):
                    i.pop("userReview")
                results.append(i)
            await asyncio.gather(*[extract_results(i) for i in data[0]["gadgets"]["data"]])
            await session.close()
            print(time.time() - starttime)
            return results
            
        else:
            return {"error": True, "error_message": "No results found"}
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {"error": True, "error_message": str(e)}


async def fetch_gadgets360(query: str):
    session = aiohttp.ClientSession()
    starttime = time.time()
    r = await session.get(f"https://gadgets360.com/search?searchtext={query}")
    soup = BeautifulSoup(await r.content.read(), "html.parser")
    results = []
    async def extract_results(item):
        title = item.find("img")["title"]
        cont = BeautifulSoup(
            await (await session.get(item.find("a")["href"])).content.read(), "html.parser"
        )
        req = cont.find_all("div", "_pdsd")
        jsun = {"title": title}
        async def fp_in_req(fp):
            ty = fp.findNext()
            jsun.update({ty.text: ty.findNext().text})
        await asyncio.gather(*[fp_in_req(i) for i in req])
        results.append(jsun)
    await asyncio.gather(*[extract_results(item) for item in soup.find_all("div", class_="rvw-imgbox")])
    print(time.time() - starttime)
    await session.close()
    return results


app = fastapi.FastAPI()


@app.get("/gadgetsnow/{query}")
async def gadgetsnow_search(query: str):
    return await fetch_url(
        "https://www.gadgetsnow.com/single_search.cms?q=" + query + "&tag=product"
    )


@app.get("/gadgets360/{query}")
async def gadgets360_search(query: str):
    return await fetch_gadgets360(query)


uvicorn.run(app, host="0.0.0.0", port=os.getenv("PORT", 8080))
