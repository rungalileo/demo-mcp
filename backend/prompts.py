
analyze_customer_call_prompt = """
    Analyze the buyer sentiment from this transcript. 
    Return the intent, and a 1-2 line explanation in JSON.
    Intent options: 
    Less likely to buy, 
    Neutral, 
    Unsure, 
    Likely to buy, 
    Very likely to buy
    
    If there is any explicit frustration, hesitation, or uncertainty in buying - choose Less likely to buy.
    Choose 'Very likely to buy' only if there is strong interest from the buyer 
    i.e. they mention they love the product.

    Strictly return raw JSON with 2 fields: buyer_intent and explanation, no other surrounding text.

    In the explanation text, include why the buyer is feeling that way.

    Format the explanation as a single string.
    Please provide your response without using markdown formatting like **, ##.
    Keep each section brief and only include information explicitly mentioned in the transcript.

    -- STARTTRANSCRIPT --
    {full_transcript}
    -- END TRANSCRIPT --
"""

champion_prompt = """
    You are a smart Sales Operations Analyst that analyzes Sales calls.
    You are given a transcript of what a potential buyer of Galileo said.
    Your job is to identify the champion of the call.

    DEFINITION OF CHAMPION:
    A champion is defined as someone who really loves the product and shows strong intent towards using or buying it. In this case the product is Galileo. Only assign champion as True if someone has sung high praises of the product or has exclaimed a desire to use or buy Galileo.
    For the explanation, be specific to this peron's thoughts, comments or feelings (whether they are positive or negative).

    DEFINITION OF BUSINESS PAIN:
    Business Pain refers to the challenges mentioned by the buyer (around LLM or Gen AI Evaluation and Observability)
    It could be a technical challenge, process challenge, or business challenge.

    Analyze the transcript and strictly return a JSON with the following fields:
    - champion: true or false (use lowercase, JSON boolean values)
    - explanation: A one-line explanation on why this person is a champion (or not a champion)
    - business_pain: A one-line description of the pain or problem

    GUIDELINES:
    1. Base your analysis solely on the evidence in the transcript
    2. Include specific quotes or paraphrases that justify your conclusion
    3. Focus on actions and statements that indicate buying influence, not just positive comments
    4. Consider both explicit statements and implicit indicators of championship
    
    Transcript:
    {transcript}

    STRICTLY return the JSON, nothing else. Use proper JSON boolean values (true/false, not True/False).
"""

business_pain_prompt = """
    Analyze this transcript and extract the challenges mentioned.
    Challenges can be business or technical.
    Return a JSON array of pain points, where each pain point is a string.
    Do not include the keyword 'json' in your response, return the array directly.
    
    Transcript:
    {full_transcript}

    Return only the JSON array of pain points, nothing else.
"""

company_name_prompt = """
    Extract name of the company from this call title.
    Call title: {call_title}
    
    Rules:
    1. If the title contains " - New Deal", extract everything before it
    2. If the title contains " <> ", extract everything before it
    3. If the title contains " - ", extract everything before it
    4. Exclude suffixes like "inc", "llc", "holdings", "technologies", "group", "corp", "company", "corporation" etc. from the company name
    5. For a healthcare company, exclude "health" or "healthcare" from the company name
    6. Remove any leading/trailing whitespace
    7. Return multiple possible variants of the company name, if applicable, such as abbreviations or common short forms (separated by spaces)
    8. If you cannot find the company name, return "Unknown Company"

    For the following companies, return their short form:
    - "American Express" -> "Amex"
    - "Deutsche Bank" -> "DB"
    - "Deutsche Telekom" -> "DT"
    - "FreshWorks" -> "FW"
    
    Examples:
    - "Notable - New Deal" -> "Notable"
    - "Intro: Cascade <> Galileo" -> "Cascade"
    - "Washington Post - New Deal" -> "Washington Post WashPost WaPo"
    - "General Dynamics Land Systems - New Deal" -> "General Dynamics Land Systems GDLS"
    - "Company Name - Some Text" -> "Company Name"

    EXCEPTIONS:
    - "ItsaCheckmate" -> "Checkmate"
    
    Only return the name(s) of the company in a format that could include the full name, abbreviation, or any widely recognized short form.
    Assume that Galileo is not a company name.
"""


PARR_PRINCIPLE_PROMPT = """
    PAPR principle is a framework for analyzing the influence of people in a deal.
    It stands for Pain, Authority, Preference, and Role.

    Here's how it works:

    Take every influencer involved in your deal.
    Rank them on these aspects on a scale of 1-5:

    ::::: PAIN :::::
    How intense (or not) is their pain for what you solve?
    Low? Medium? High?

    ::::: AUTHORITY :::::
    How much authority do they (or could they) have on this deal?
    Low? Medium? High?


    ::::: PREFERENCE :::::
    How highly do they prefer your solution vs. someone else's?
    Low? Medium? High?

    ::::: ROLE :::::
    How involved are they in this particular decision process?
    Low? Medium? High?

    Here's an example:

    Let's say I have a director of sales involved in my deal. 

    Here's how she stacks up:

    PAIN: Very high.
    AUTHORITY: High. She's not the DM, but her voice is respected.
    PREFERENCE: Low. She prefers a competitor.
    ROLE: High. Very involved in the decision process.

    What's your move?
    You can't ignore her.
    Her authority is too high. 
    You'll lose.
    My move?
    Find an internal coach.
    Learn why she prefers the competitor.
    If it's non emotional (i.e. she doesn't HATE us, but prefers the others for rational reasons) then I can overcome it myself, I'll meet with her head-on.
    Turn a skeptic into a champion.
    But if she HATES us for some reason?
    My words may carry no influence.
    So I'll enlist my champion to sell on my behalf.
    Now. Here's where things get powerful:

    Take the opposite example:

    Let's say I have A DIFFERENT director of sales involved in my deal. 

    Here's how he stacks up:

    PAIN: Very high.
    AUTHORITY: Low. Not respected. Coach says people don't like him.
    PREFERENCE: Low. He prefers a competitor to pclub.io.
    ROLE: Somewhat high. Involved in the decision process.

    What's your move?
    Polar opposite as before.

    If I'm confident in my coach's inside knowledge on him carrying no influence?
    I'm going to ignore him.

    Box him out of the deal (I'm such a meanie I know).
    The point of all of this?

    The PAPR framework eliminate random acts of multi-threading.
    You can see that based on how they rank, your actions will differ.
    That's how you dramatically boost your win rates with multi-threading.

    Rank this person on the PAPR criteria.

    Return a JSON with the following fields:
    - pain: 1-5
    - authority: 1-5
    - preference: 1-5
    - role: 1-5
    - parr_explanation: A one-line explanation of the analysis based on the PAPR framework

    Speaker: {speaker_name}
    Transcript:
    {transcript}

    STRICTLY return the JSON, nothing else.
"""


