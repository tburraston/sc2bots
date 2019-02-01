from functools import reduce
from operator import or_
import random
import asyncio
import math

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.data import race_townhalls

import enum

class TwoBaseRoach(sc2.BotAI):

  def __init__(self):
    self.has_natural = False
    self.bm = True
    self.current_build_item = None
    self.current_action_item = None
    self.gen = None
    self.gen2 = None

    self.action_queue = [
      ['scoutnat', False]
    ]

    self.build_queue = [
      ['drone', False],  # 13 of 14
      ['overlord', False],
      ['drone', False ],  # 14 of 23
      ['drone', False ],  # 15 of 23
      ['drone', False ],  # 16 of 23
      ['drone', False ],  # 17 of 23
      ['hatchery', False ],
      ['drone', False ],  # 17 of 23
      ['spawningpool', False ],
      ['drone', False ],  # 17 of 23
      ['drone', False ],  # 18 of 23
      ['drone', False ],  # 19 of 23
      ['firstextractor', False ],
      ['drone', False ],  # 19 of 23
      ['overlord', False ],
      ['drone', False ],  # 20 of 30
      ['drone', False ],  # 21 of 30
      ['drone', False ],  # 22 of 30
      ['drone', False ],  # 23 of 30
      ['drone', False ],  # 24 of 30
      ['drone', False ],  # 25 of 30
      ['drone', False ],  # 26 of 30
      ['drone', False ],  # 27 of 30
      ['overlord', False ],
      ['roachwarren', False ],
    ]

  def select_target(self):
    if self.known_enemy_structures.exists:
      return random.choice(self.known_enemy_structures).position

      return self.enemy_start_locations[0]

  async def enemy_natural(self):
    closest = None
    distance = math.inf
    for ex in self.expansion_locations:
      def is_near_to_expansion(t):
        return t.position.distance_to(ex) < self.EXPANSION_GAP_THRESHOLD
      enemy_start = self.enemy_start_locations[0]
      d = await self._client.query_pathing(enemy_start, ex)
      if d is None:
        continue
      if d < distance:
        distance = d
        closest = ex
    return closest

  async def glhf(self):
    if self.bm:
      self.bm = False
      await self.chat_send('(glhf)')

  async def perform_action(self):
    if self.current_action_item == None:
      pass
    elif self.current_action_item[0] == 'scoutnat':
      overlord = self.units(OVERLORD).random
      err = await self.do(overlord.move(await self.enemy_natural()))
      await asyncio.sleep(.5)
      self.current_action_item[1] = True if not err else False

  async def perform_build_action(self, larvae):
    if self.current_build_item == None:
      pass
    elif self.current_build_item[0] == 'drone':
      if self.can_afford(DRONE) and larvae.exists:
        err = await self.do(larvae.random.train(DRONE))
        await asyncio.sleep(.5)
        self.current_build_item[1] = True if not err else False
    elif self.current_build_item[0] == 'roach':
      if self.can_afford(ROACH) and larvae.exists:
        err = await self.do(larvae.random.train(ROACH))
        await asyncio.sleep(.5)
        self.current_build_item[1] = True if not err else False
    elif self.current_build_item[0] == 'overlord':
      if self.can_afford(OVERLORD) and larvae.exists:
        err = await self.do(larvae.random.train(OVERLORD))
        await asyncio.sleep(.5)
        self.current_build_item[1] = True if not err else False
    elif self.current_build_item[0] == 'hatchery':
      if self.can_afford(HATCHERY):
        err = await self.expand_now()
        await asyncio.sleep(.5)
        self.current_build_item[1] = True if not err else False
    elif self.current_build_item[0] == 'spawningpool':
      if self.can_afford(SPAWNINGPOOL) and not self.already_pending(SPAWNINGPOOL):
        err = await self.build(SPAWNINGPOOL, near=self.state.vespene_geyser.closest_to(self.hq))
        await asyncio.sleep(.5)
        self.current_build_item[1] = True if not err else False
    elif self.current_build_item[0] == 'roachwarren':
      if self.can_afford(ROACHWARREN) and not self.already_pending(ROACHWARREN):
        err = await self.build(ROACHWARREN, near=self.hq)
        await asyncio.sleep(.5)
        self.current_build_item[1] = True if not err else False
    elif self.current_build_item[0] == 'firstextractor':
      if self.can_afford(EXTRACTOR) and not self.already_pending(EXTRACTOR):
        drone = self.workers.random
        target = self.state.vespene_geyser.closest_to(drone.position)
        err = await self.do(drone.build(EXTRACTOR, target))
        await asyncio.sleep(.5)
        self.current_build_item[1] = True if not err else False
    elif self.current_build_item[0] == 'queen':
      if self.units(QUEEN).amount + self.already_pending(QUEEN) < 1:
        furthest_townhall = self.hq
      else:
        furthest_townhall = self.townhalls.furthest_to(self.hq.position)
      if self.can_afford(QUEEN) and furthest_townhall.is_ready and furthest_townhall.noqueue:
        err = await self.do(furthest_townhall.train(QUEEN))
        await asyncio.sleep(.5)
        self.current_build_item[1] = True if not err else False

  async def check_queens(self):
    if self.units(SPAWNINGPOOL).ready.exists:
      if self.units(QUEEN).amount < self.townhalls.amount and ['queen', False] not in self.build_queue:
        self.build_queue.insert(0, ['queen', False])
        await asyncio.sleep(.5)

  async def need_overlords(self):
    if self.supply_left < 5 and self.supply_cap < 200 and self.build_queue.count(['overlord', False]) == 0:
      self.build_queue.insert(0, ['overlord', False])
      await asyncio.sleep(.5)

  async def need_roaches(self):
    if self.units(ROACHWARREN).ready.exists and self.units(ROACH).amount + self.build_queue.count(['roach', False]) < 15:
      self.build_queue.append(['roach', False])
      await asyncio.sleep(.5)

  async def need_drones(self):
    for townhall in self.townhalls:
      eventual_workers = townhall.assigned_harvesters + self.already_pending(DRONE) + self.build_queue.count(['drone', False])
      if eventual_workers < townhall.ideal_harvesters + 6:
        self.build_queue.append(['drone', False])
        await asyncio.sleep(.5)

  async def always_inject(self):
    for queen in self.units(QUEEN).idle:
      abilities = await self.get_available_abilities(queen)
      if AbilityId.EFFECT_INJECTLARVA in abilities:
        await self.do(queen(EFFECT_INJECTLARVA, self.townhalls.closest_to(queen.position)))

  async def on_step(self, iteration):
    larvae = self.units(LARVA)
    forces = self.units(ZERGLING) | self.units(HYDRALISK)
    self.hq = self.townhalls.first
    await self.glhf()
    await self.distribute_workers()

    if self.current_action_item == None or self.current_action_item[1] == True:
      self.current_action_item = self.action_queue.pop(0) if len(self.action_queue) >= 1 else None
    await self.perform_action()

    if self.current_build_item == None or self.current_build_item[1] == True:
      self.current_build_item = self.build_queue.pop(0) if len(self.build_queue) >= 1 else None
      print(self.build_queue)
    await self.perform_build_action(larvae)

    await self.check_queens()
    await self.always_inject()

    await self.need_overlords()
    await self.need_roaches()
    await self.need_drones()

def main():
  sc2.run_game(sc2.maps.get("(2)CatalystLE"), [
    Bot(Race.Zerg, TwoBaseRoach()),
    Computer(Race.Terran, Difficulty.Medium)
  ], realtime=True, save_replay_as="ZvT-roach.SC2Replay")

if __name__ == '__main__':
  main()
