Write one Python file jarvis/model.py. Output exactly in builder format.
Implement class LocalModels:
- __init__(self, tools): assign self.tools=tools and self.agent=None; do not initialize model or import cactus.
- propose(self, text): set os.environ['CACTUS_TELEMETRY']='0' and os.environ['HF_HUB_OFFLINE']='1'; import cactus; if self.agent is None set self.agent=cactus.Cactus(tools=self.tools); return self.agent.complete(text).
- reset(self): if self.agent is not None call self.agent.reset().
- transcribe(self, wav): set os.environ['CACTUS_TELEMETRY']='0' and os.environ['HF_HUB_OFFLINE']='1'; import cactus; return cactus.transcribe(wav)['text'].
Use exactly these API names. No other behavior. Include no other files.
