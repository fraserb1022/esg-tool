import requests
from bs4 import BeautifulSoup

def scrape_esg_scores(ticker: str):
    url = f"https://finance.yahoo.com/quote/{ticker}/sustainability/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    def get_score(testid):
        section = soup.find("section", {"data-testid": testid})
        if not section:
            return None, None
        score_tag = section.find("h4")
        level_tag = section.find("span", class_="perf yf-y3c2sq")  # may not always exist
        score = float(score_tag.text.strip()) if score_tag else None
        level = level_tag.text.strip() if level_tag else None
        return score, level

    total_score, total_level = get_score("TOTAL_ESG_SCORE")
    env_score, _ = get_score("ENVIRONMENTAL_SCORE")
    soc_score, _ = get_score("SOCIAL_SCORE")
    gov_score, _ = get_score("GOVERNANCE_SCORE")

    # Product Involvement Areas
    involvement_section = soup.find("section", {"data-testid": "involvement-areas"})
    involvement_data = {}
    if involvement_section:
        table = involvement_section.find("table")
        if table:
            rows = table.find_all("tr")
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) == 2:
                    product = cols[0].text.strip()
                    involvement = cols[1].text.strip()
                    involvement_data[product] = involvement

    # ESG Controversy
    controversy_section = soup.find("section", {"data-testid": "esg-controversy"})
    controversy_score = None
    category_average = None
    if controversy_section:
        # The numeric controversy score is inside a <span> under a div with class 'val yf-ye6fz0'
        val_div = controversy_section.find("div", class_="val yf-ye6fz0")
        if val_div:
            spans = val_div.find_all("span")
            if spans and len(spans) >= 2:
                try:
                    controversy_score = float(spans[0].text.strip())
                except:
                    pass
        
        # Category average score is inside the tooltip div, find spans with classes 'peer-score'
        tooltip_div = controversy_section.find("div", class_="tooltip al-top yf-15g2hux")
        if tooltip_div:
            peer_span = tooltip_div.find("span", class_="peer-score yf-ye6fz0")
            if peer_span:
                try:
                    category_average = float(peer_span.text.strip())
                except:
                    pass

    return {
        "total": total_score,
        "total_level": total_level,
        "environmental": env_score,
        "social": soc_score,
        "governance": gov_score,
        "involvement_areas": involvement_data,
        "controversy_score": controversy_score,
        "controversy_category_average": category_average,
    }
