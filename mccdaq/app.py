#!/usr/bin/env python3

import asyncio
import aiohttp
from aiohttp import web
import aiohttp_jinja2
import jinja2
import datetime
import os
from random import randint

from joule import FilterModule, api, utilities

CSS_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'css')
JS_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'js')
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'templates')
print(TEMPLATES_DIR)


class EncoderApp(FilterModule):

    async def setup(self, parsed_args, app, inputs, outputs):
        # useful variables
        self.save_data = False
        self.zero = [0, 0, 0]
        self.data_in = inputs["input"]
        self.data_out = outputs["output"]
        self.close_interval = False
        self.filename = ""
        self.annotation = None
        loader = jinja2.FileSystemLoader(TEMPLATES_DIR)

        aiohttp_jinja2.setup(app, loader=loader)

    async def run(self, parsed_args, inputs, outputs):

        # temporary variables for testing
        # count = 0
        # await self.save_data_start()
        while not self.stop_requested:
            data = await self.data_in.read()
            self.data_in.consume(len(data))

            # if save_data is true, write data + offset
            if self.save_data:
                data['data'] -= self.zero
                await self.data_out.write(data)
                if self.annotation is not None and self.annotation.start is None:
                    self.annotation.start = int(data['timestamp'][0])
            elif self.close_interval:
                if self.annotation is not None:
                    self.annotation.end = int(data['timestamp'][-1])
                    await self.node.annotation_create(self.annotation, self.data_out.stream)

                self.close_interval = False
                await self.data_out.close_interval()
            self.cur_Pos = data['data'][-1]
            await asyncio.sleep(1)

    def routes(self):
        return [
            web.get('/', self.index),
            web.post('/start.json', self.start_capture),
            web.post('/stop.json', self.stop_capture),
            web.get('/status.json', self.get_status),
            web.static('/assets/css', CSS_DIR),
            web.static('/assets/js', JS_DIR)
        ]

    async def start_capture(self, request):
        print("starting data save")
        data = await request.post()
        time = datetime.datetime.now()
        timestamp = time.strftime('%Y-%m-%d--%H-%M-%S')

        self.filename = "%s[%s].avi" % (data['title'], timestamp )
        self.zero = self.cur_Pos
        # turn on flag to save data
        self.save_data = True
        self.annotation = api.Annotation(title=data['title'], content=data['content'], start=None)
        return await self.get_status(request)

    async def stop_capture(self, request):
        print("stopping data save")
        self.close_interval = True
        self.save_data = False
        return await self.get_status(request)

    async def get_status(self, request):
        return web.json_response(({'recording': self.save_data,
                                   'filename': self.filename}))

    @aiohttp_jinja2.template('index.jinja2')
    async def index(self, request):
        return {'recording': self.save_data}


def main():
    r = EncoderApp()
    r.start()


if __name__ == "__main__":
    main()
