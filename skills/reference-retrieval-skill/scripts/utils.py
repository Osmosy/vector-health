import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
import time
import json

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def fetch_details(id_list):
    """
    Fetch details for a list of PubMed IDs.
    """
    if not id_list:
        return []
    
    # User requested to allow batch retrieval (PMIDs given together)
    ids = ",".join(id_list)
    params = {
        "db": "pubmed",
        "id": ids,
        "retmode": "xml"
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{EFETCH_URL}?{query_string}"
    
    papers = []
    try:
        # Rate limit: Sleep 1.1s to strictly comply with 1 request/second limit
        time.sleep(1.1)
        
        with urllib.request.urlopen(url) as response:
            xml_data = response.read().decode()
            root = ET.fromstring(xml_data)
            
            for article in root.findall(".//PubmedArticle"):
                paper = {}
                medline_citation = article.find("MedlineCitation")
                article_data = medline_citation.find("Article")
                
                # PMCID/PMID for reference
                pmid_node = medline_citation.find("PMID")
                if pmid_node is None or not pmid_node.text:
                    continue # Skip papers without a valid PMID
                
                pmid = pmid_node.text
                paper["pmid"] = pmid
                paper["pubmed_url"] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"

                # Title
                title_node = article_data.find("ArticleTitle")
                paper["title"] = title_node.text if title_node is not None else "No title available"
                
                # Abstract
                abstract_text = []
                abstract = article_data.find("Abstract")
                if abstract is not None:
                    for abstract_text_elem in abstract.findall("AbstractText"):
                        if abstract_text_elem.text:
                            label = abstract_text_elem.get("Label")
                            if label:
                                abstract_text.append(f"{label}: {abstract_text_elem.text}")
                            else:
                                abstract_text.append(abstract_text_elem.text)
                paper["abstract"] = " ".join(abstract_text) if abstract_text else "No abstract available."
                
                # Year and Journal
                journal = article_data.find("Journal")
                if journal is not None:
                    # Journal Title
                    journal_title = journal.find("Title")
                    journal_iso = journal.find("ISOAbbreviation")
                    paper["journal"] = journal_iso.text if journal_iso is not None else (journal_title.text if journal_title is not None else "")

                    # PubDate
                    pub_date = journal.find("JournalIssue").find("PubDate")
                    if pub_date is not None:
                        year = pub_date.find("Year")
                        if year is not None:
                            paper["year"] = year.text
                        else:
                            medline_date = pub_date.find("MedlineDate")
                            if medline_date is not None:
                                paper["year"] = medline_date.text.split(" ")[0] 
                            else:
                                paper["year"] = "Unknown"
                else:
                    paper["journal"] = ""
                    paper["year"] = "Unknown"

                # Authors
                author_list = []
                authors = article_data.find("AuthorList")
                if authors is not None:
                    for author in authors.findall("Author"):
                        last_name = author.find("LastName")
                        initials = author.find("Initials")
                        if last_name is not None and initials is not None:
                            author_list.append(f"{last_name.text} {initials.text}")
                        elif last_name is not None:
                            author_list.append(last_name.text)
                paper["authors"] = author_list

                # Check for Open Access (PMC ID)
                pmc_id = None
                pubmed_data = article.find("PubmedData")
                if pubmed_data is not None:
                    article_id_list = pubmed_data.find("ArticleIdList")
                    if article_id_list is not None:
                        for article_id in article_id_list.findall("ArticleId"):
                            if article_id.get("IdType") == "pmc":
                                pmc_id = article_id.text
                                break
                                
                # Check for PMC ID in Medline OtherID as a fallback
                if not pmc_id:
                     for other_id in medline_citation.findall("OtherID"):
                         if other_id.get("Source") == "NLM" and other_id.text and other_id.text.startswith("PMC"):
                             pmc_id = other_id.text
                             break
                
                paper["is_oa"] = pmc_id is not None
                if pmc_id:
                    paper["pmcid"] = pmc_id

                papers.append(paper)
                
    except Exception as e:
         print(f"Error fetching details: {e}", file=sys.stderr)
         
    return papers
