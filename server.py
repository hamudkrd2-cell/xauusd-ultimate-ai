import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI

app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=12*1024*1024
MODEL=os.getenv("OPENAI_VISION_MODEL","gpt-5.6-luna")
client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SCHEMA={"type":"object","properties":{
"decision":{"type":"string","enum":["BUY","SELL","WAIT"]},"confidence":{"type":"integer","minimum":0,"maximum":100},
"timeframe":{"type":"string"},"setup":{"type":"string"},"bias":{"type":"string"},"entry_zone":{"type":"string"},
"stop_loss":{"type":"string"},"risk_reward":{"type":"string"},"tp1":{"type":"string"},"tp2":{"type":"string"},"tp3":{"type":"string"},
"support_resistance":{"type":"string"},"reason":{"type":"string"},"confirmation":{"type":"string"},"invalidation":{"type":"string"}
},"required":["decision","confidence","timeframe","setup","bias","entry_zone","stop_loss","risk_reward","tp1","tp2","tp3","support_resistance","reason","confirmation","invalidation"],"additionalProperties":False}

INSTRUCTIONS="""You are an expert XAUUSD technical-chart vision analyst.
Analyze only visible evidence in the uploaded screenshots. Never invent a price that cannot be read.
Use market structure (HH/HL/LH/LL), trend, break of structure, liquidity sweeps, support/resistance, supply/demand, breakout/retest, rejection, candlestick context and visible indicators.
If evidence conflicts or the setup is weak, choose WAIT.
Return exactly one of BUY, SELL, WAIT.
Confidence is evidence strength, not a probability of profit.
For numeric entry/SL/TP, use only clearly readable chart prices; otherwise say not reliably readable.
Do not place orders."""

@app.get("/")
def home(): return send_from_directory(".", "index.html")
@app.get("/health")
def health(): return jsonify({"ok":True,"model":MODEL,"ai_key_configured":bool(os.getenv("OPENAI_API_KEY"))})

@app.post("/api/analyze")
def analyze():
    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({"error":"OPENAI_API_KEY is not configured on the online server."}),500
    imgs=request.files.getlist("charts")
    if not imgs:return jsonify({"error":"No chart screenshot was uploaded."}),400
    imgs=imgs[:3]
    tf=request.form.get("timeframe","M5"); style=request.form.get("style","Scalp")
    content=[{"type":"input_text","text":f"Analyze XAUUSD for a {style} plan. Primary timeframe: {tf}. If multiple screenshots exist, use them as multi-timeframe context and reconcile conflicts. Prefer WAIT to forcing a trade."}]
    for f in imgs:
        raw=f.read()
        mime=f.mimetype if f.mimetype in ("image/jpeg","image/png","image/webp") else "image/jpeg"
        content.append({"type":"input_image","image_url":f"data:{mime};base64,{base64.b64encode(raw).decode()}","detail":"high"})
    try:
        resp=client.responses.create(model=MODEL,instructions=INSTRUCTIONS,input=[{"role":"user","content":content}],
            text={"format":{"type":"json_schema","name":"xauusd_analysis","schema":SCHEMA,"strict":True}})
        return jsonify(json.loads(resp.output_text))
    except Exception as e:
        return jsonify({"error":"AI request failed: "+str(e)}),500

@app.errorhandler(413)
def too_large(e): return jsonify({"error":"Screenshots are too large. Use smaller/compressed images."}),413
@app.errorhandler(Exception)
def general(e): return jsonify({"error":"Server error: "+str(e)}),500

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","8080")))
