#!/usr/bin/env python3

import asyncio
from aiohttp import web
import aiohttp_jinja2
import jinja2
import os
from random import randint

from joule import FilterModule, EmptyPipe

CSS_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'css')
JS_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'js')
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'templates')
print(TEMPLATES_DIR)

class BootstrapInterface(FilterModule):

    async def setup(self, parsed_args, app, inputs, outputs):
        #useful variables
        self.save_data = False
        self.Xoffset = 0
        self.Yoffset = 0
        self.Zoffsert = 0
        self.data_in = inputs["input"]
        self.data_out = outputs["output"]

        
        loader = jinja2.FileSystemLoader(TEMPLATES_DIR)
        
        print("setting up")
        aiohttp_jinja2.setup(app, loader=loader)

    async def run(self, parsed_args, inputs, outputs):
        print("running")


        #temporary variables for testing
        #count = 0
        #await self.save_data_start()



        
        
        while True:
            # read into local var
            cur_data = await self.data_in.read()
            
            # consume from input
            self.data_in.consume(len(cur_data))
            
            # if save_data is true, write data + offset
            if self.save_data:
                #need to add offsets here

                for sample in cur_data:
                    sample[1][0] = sample[1][0] + self.Xoffset
                    sample[1][1] = sample[1][1] + self.Yoffset
                    sample[1][2] = sample[1][2] + self.Zoffset


                
                await self.data_out.write(cur_data)
            self.cur_Pos = cur_data[len(cur_data)-1][1] #[x,y,z]    
            await asyncio.sleep(1)
            #count = count +1
            #if count == 1:
            #    await self.save_data_stop()

    def routes(self):
        return [
            web.get('/', self.index),
            web.get('/index.html', self.index),
            web.get('/data.json', self.data),
            web.post('/turnon',self.start_wrapper),
            web.post('/turnoff',self.stop_wrapper),
            web.static('/assets/css', CSS_DIR),
            web.static('/assets/js', JS_DIR)
        ]

    async def save_data_start(self):
        print("starting data save")
        #calculate offsets
        #cur_data = await self.data_in.read()
        #last = len(cur_data)-1
        
        
        curX = self.cur_Pos[0]
        curY = self.cur_Pos[1]
        curZ = self.cur_Pos[2]
        #print(curX)
        #print(curY)
        #print(curZ)



        
        self.Xoffset = -1*curX
        self.Yoffset = -1*curY
        self.Zoffset = -1*curZ

        #turn on flag to save data
        self.save_data = True

    async def save_data_stop(self):
        print("stopping data save")
        self.save_data = False
        await self.data_out.close_interval()



    async def start_wrapper(self, request):
        print("start wrapper called")
        await self.save_data_start()
        raise web.HTTPFound(location="index.html")


    
    async def stop_wrapper(self, request):
        print("stop wrapper called")
        await self.save_data_stop()
        raise web.HTTPFound(location="index.html")
        
    @aiohttp_jinja2.template('index.jinja2')
    async def index(self, request):
        return {'recording_on': self.save_data}


    

    # json end point for AJAX requests
    async def data(self, request):
        # return summary statistics, etc.
        return web.json_response(data={'random_value': randint(0, 10)})


def main():
    r = BootstrapInterface()
    r.start()


if __name__ == "__main__":
    main()
