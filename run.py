


from bs4 import BeautifulSoup
import requests
import pickle
import os
import json
import time


def fetchItemIDs():

	with open("wiki.pickle", 'rb') as handle:
		wikiData = pickle.load(handle)	
	
	for name in list(wikiData.keys()):
		
		link = "https://xivapi.com/search?string=" + name
		
		time.sleep(0.05)
		print("fetching id for " + name)
		r = requests.get(link)
		
		if r.status_code != 200:
			print("got a {:d} when attempting to fetch item ids, exiting".format(r.status_code))
			exit(1)
		
		try:
			itemID = r.json()["Results"][0]["ID"]
		except:
			itemID = -1
		
		wikiData[name]["ID"] = itemID
		
	with open('wiki.pickle', 'wb') as handle:
		pickle.dump(wikiData, handle, protocol=pickle.HIGHEST_PROTOCOL)
	

	pass

def fetchWikiPrices():

	with open("wiki.pickle", 'rb') as handle:
		wikiData = pickle.load(handle)	
	
	for name, data in wikiData.items():
		
		if not data["hasPurchase"]:
			continue
			
		time.sleep(0.1)
		print("fetching " + name)
		r = requests.get("https://ffxiv.consolegameswiki.com" + data["link"])
		
		if r.status_code != 200:
			print("got a {:d} when attempting to fetch item prices, exiting".format(r.status_code))
			exit(1)
		
		soup = BeautifulSoup(r.text, 'html.parser')
		soup = soup.find("div", {"class": "infobox-n item"})
			
		if soup is None:
			# most likely, we need to follow to a sublink here.
			soup = BeautifulSoup(r.text, 'html.parser')
			soup = soup.find("div", {"class": "mw-parser-output"})
			soup = soup.find("ul")
			soup = soup.find_all("li")
			
			for s in soup:
				
				newLink = s.find("a", recursive=False)["href"]
				
				if "item" in newLink.lower() or "furnish" in newLink.lower():
					break
					
			else:
				print("unable to find a proper link for item {:s}, exiting".format(name))
				exit(1)
			
			wikiData[name]["link"] = newLink
			
			r = requests.get("https://ffxiv.consolegameswiki.com" + newLink)
		
			if r.status_code != 200:
				print("got a {:d} when attempting to fetch item prices, exiting".format(r.status_code))
				exit(1)
			
			soup = BeautifulSoup(r.text, 'html.parser')
			soup = soup.find("div", {"class": "infobox-n item"})
		
		
		soup = soup.find("dl")
		
		dt = soup.find_all("dt")
		dd = soup.find_all("dd")
		
		if len(dd) != len(dt):
			print("something is very, very wrong")
			print("when fetching table information from the wiki")
			print("the lengths of the columns were not equal. exiting")
			exit(1)
			
		for i in range(0, len(dt)):
			if dt[i].text.lower().strip() == "cost":
				wikiData[name]["price"] = int(dd[i].text.strip().replace(",", ""))
	
	
	
	with open('wiki.pickle', 'wb') as handle:
		pickle.dump(wikiData, handle, protocol=pickle.HIGHEST_PROTOCOL)
	
		
	pass
	
def parseHousingItems():

	files = os.listdir("./wikiData/")
	files.remove("base.pickle")
	
	res = {}
	
	for f in files:
		
		tempRes = {}
		
		with open("./temp/" + f, 'rb') as handle:
			text = pickle.load(handle)
			
		soup = BeautifulSoup(text, 'html.parser')
		soup = soup.find("div", {"class": "mw-parser-output"})
		soup = soup.find("table")
		soup = soup.find_all("tr")[1:]
		
		for s in soup:
		
			# this step induces a lot of lag, but it doesnt matter, as wiki  
			# data will not be updated often
			for br in s.find_all("br"):
				br.replace_with("\n")
		
			data = s.find_all("td")
			
			name = data[0].text.strip()
			location = data[2].text.strip()
			
			
			#print(name, location)
				
			if name in res:
				res[name]["type"].append(f[4:-7])
				continue
				
			res[name] = {}
			res[name]["link"] = data[0].find("a")["href"]
			res[name]["locations"] = location.split("\n")				
			res[name]["type"] = [ f[4:-7] ]
			res[name]["hasPurchase"] = "purchase" in location.lower()
			
		#res[f[4:-7]] = tempRes
			
	#print(res.keys())

	#temp = res[list(res.keys())[6]]
	#print(json.dumps(temp, indent=4, sort_keys=True))
	
	with open('wiki.pickle', 'wb') as handle:
		pickle.dump(res, handle, protocol=pickle.HIGHEST_PROTOCOL)
	
	pass

def fetchHousingWiki():

	r = requests.get("https://ffxiv.consolegameswiki.com/wiki/Housing_Items")
	text = r.text
	with open('./temp/base.pickle', 'wb') as handle:
		pickle.dump(text, handle, protocol=pickle.HIGHEST_PROTOCOL)

	soup = BeautifulSoup(text, 'html.parser')
	
	soup = soup.find_all("span", {"class": "mw-headline"})
	
	subLinks = []
	
	for s in soup:
		subLinks.append(s.find("a")["href"])
	
	
	mainLink = "https://ffxiv.consolegameswiki.com"
	
	for l in subLinks:
		link = mainLink + l 
			
		r = requests.get(link)
		
		filename = l.replace("/", "")
		
		print(r.status_code)
		print(filename)
		
		text = r.text
		with open("./temp/" + filename + ".pickle", 'wb') as handle:
			pickle.dump(text, handle, protocol=pickle.HIGHEST_PROTOCOL)
		
	
		
	pass
	
def updateWikiData():

	fetchHousingWiki()
	parseHousingItems()
	fetchWikiPrices()
	fetchItemIDs()
	
	pass
		
def findTrades():

	with open("wiki.pickle", 'rb') as handle:
		wikiData = pickle.load(handle)	
	
	validData = {}
	
	for name, data in wikiData.items():
		if data["hasPurchase"] and "price" in data and data["ID"] != -1:
			validData[name] = data
	
	size = 90 # actually 100, just staying safe
	names = list(validData.keys())
	nameChunks = [names[i:i + size] for i in range(0, len(names), size)]

	itemData = {}

	for chunk in nameChunks:
	
		if len(chunk) == 1:
			continue
	
		itemIDs = []
		for name in chunk:
			itemIDs.append(validData[name]["ID"])
		
		
		idk = ",".join(map(str, itemIDs))
		
		link = "https://universalis.app/api/v2/midgardsormr/" + ",".join(map(str, itemIDs))
		r = requests.get(link)
		
		dataChunk = r.json()
		itemData = {**itemData, **dataChunk}
	
	
	idToName = {}
	for name, data in wikiData.items():
		if data["ID"] == -1:
			continue
			
		idToName[data["ID"]] = name
	
	
	final = []
	
	for id, data in itemData["items"].items():
		if data["nqSaleVelocity"] == 0:
			continue
	
		tempFinalData = {
		
			"name": idToName[int(id)],
		
			"ID": int(id),
			#"velocity": data["nqSaleVelocity"], 
			"velocity": data["regularSaleVelocity"], 
			
			"minPrice": data["minPrice"],
			
			"buyPrice": wikiData[idToName[int(id)]]["price"],
		
		}
		
		tempFinalData["return"] = 100 * tempFinalData["minPrice"] / tempFinalData["buyPrice"]
		
		#tempFinalData["score"] = (tempFinalData["velocity"] if tempFinalData["velocity"] > 2 else tempFinalData["velocity"] / 4) * (tempFinalData["minPrice"] / tempFinalData["buyPrice"])
		#tempFinalData["score"] = (tempFinalData["velocity"] if tempFinalData["velocity"] > 2 else tempFinalData["velocity"] / 4) * (tempFinalData["minPrice"] - tempFinalData["buyPrice"])
		#tempFinalData["score"] = tempFinalData["velocity"] * (tempFinalData["minPrice"] - tempFinalData["buyPrice"])
		#tempFinalData["score"] = (tempFinalData["minPrice"] - tempFinalData["buyPrice"])
		#tempFinalData["score"] = -(tempFinalData["minPrice"] - tempFinalData["buyPrice"])
		
		tempFinalData["score"] = tempFinalData["velocity"], 
		
		final.append(tempFinalData)
	
	final = sorted(final, key = lambda x: x["score"], reverse=True)
	
	for f in final[:20]:
		print("{:5d} {:<40s} {:7.4f} {:7d} {:7d} {:10.2f}%".format(f["ID"], f["name"], f["velocity"], f["minPrice"], f["buyPrice"], f["return"]))

	pass
	
if __name__ == "__main__":

	# callto fetch new wiki info
	#updateWikiData() 
	
	findTrades()

