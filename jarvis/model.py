import os

class LocalModels:
    def __init__(self, tools):
        self.tools = tools
        self.agent = None

    def propose(self, text):
        os.environ['CACTUS_TELEMETRY'] = '0'
        os.environ['HF_HUB_OFFLINE'] = '1'
        import cactus
        if self.agent is None:
            self.agent = cactus.Cactus(tools=self.tools)
        return self.agent.complete(text)

    def reset(self):
        if self.agent is not None:
            self.agent.reset()

    def transcribe(self, wav):
        os.environ['CACTUS_TELEMETRY'] = '0'
        os.environ['HF_HUB_OFFLINE'] = '1'
        import cactus
        return cactus.transcribe(wav)['text']
