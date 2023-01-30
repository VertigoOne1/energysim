# Home Energy Management Simulator

For simulating how your home consumes and produces energy (Home PV/Hybrid System)

## Idea

The physical part of a home PV+Battery setup is fairly well understood, but simulating how the system would function has some gaps that might be useful to some people.

Imagine being able to define your home energy consumers, producers and their properties and simulate their running in real time as actual "things" running virtually. Including weather simulation, time of day and loadshedding/outages schedules, and being able to "configure" the inverter to settings typically available to them, such as when to charge, when to discharge.

The idea is to run it as a kubernetes namespace where you define solarpanels, inverters, batteries and consumers such as ovens and TV's as containers. This then becomes your "home". These produce events, which are their energy needs or production, which then results in a nett energy mix and realtime adjustable settings for their management state, consumption, production and cost. Running the tick time at a higher rate allows you to plan out how it will change into the future, and allowing you to chang things, timers/smart switches, bigger/smaller systems to see their effect.

Overall stack: Python (because i'm most confortable with it)

Messaging Bus
crossbar.io - <https://github.com/crossbario>

Messaging and Events
twisted - <https://twisted.org/>
autobahn - <https://github.com/crossbario>

Message Schema management
Pydantic - <https://docs.pydantic.dev/>

UI
Angular - v16 and node 18

## Needs

Ability to spin up deployments on the fly on a kubernetes namespace. (Which will be the "home" your simulation is running on)
Everything is a container, the sun, the weather, the panels, the inverter, the battery, the oven, the geyser, the tv.
Lots and lots of properties, but we can start small.

## New concepts learned from this for myself

Appplication configuration management via async messages to the apps

- simulation tick speed that is propagated to every container, and ticks as messages
- property changes for specific containers

Creating kubernetes objects from a web based frontend
Drag and Drop UI?

- the home objects, CRUD for objects (helm type frontend?)
- application configuration state management

State management/Restart management

State polling

App -> prometheus for the object metrics (oven, how much power consumed?), and some grafana dashboards

Websocket application UI development stuffs (autobahn)

Crossbar and twisted is new to me, i know a bit of pydantic.

## More thoughts

Do we perhaps run the message bus as raw energy messages? The base unit of energy is the Joule. 100W = 100J/s

Kilowatt-hours - 1000J/s, for an hour, or 3.6MJ).

A 2000W oven on for 10 minutes = 2000J * 600 = 1.2MJ

if we emit an event as something using 2000J, and the event is emitted every second, that is your Watt.

so the question is do we run messages every second for Joules... as packets of energy (like running it in virtual wires)

```plain
Scenario 1
Oven -> Inverter -> -2000J (lost as heat)
Inverter -> Oven -> +2000J
Grid -> Inverter -> -2000J
```

Grid is an infinite source of Joules, the nett effect is 0 by taking the consumed Joules and turning it into a currency cost to "replenish"

```plain
Scenario 2
Oven -> Inverter -> -2000J
Inverter ->  Oven -> +2000J
Battery -> Inverter -> -2000J  (battery capacity reduction by 2000J), which needs to plus from PV/Grid to reclaim by charging
```

nett is 0, thus satisfied

you then subtract and add Joules to battery as it has a capacity of X Joules, 12KWh battery = 12000J/s*3600

```plain
PV -> Inverter -> +500J
Inverter -> Battery -> +500J
Sun -> PV -> -500J
```

The Sun is an infinite source of Joules, thus it is sinked/zero's out.

## Minimum Viable Product Definition (rough idea at the moment)

We need to simulate the sun

properties

- irridiance W/m2
- position in the sky modifier (for now)

produces - Joules

consumes - none

We need to simulate intervening weather effects

properties

- atmospheric transparency
- % cloud cover

produces - irridiance modifier

consumes - none

We need to simulate a solar panel (and be able to make multiple)

properties

- maximum capacity
- volts
- amps
- angle (later)

produces - Joules (research how this exactly works with panels, volts/amps/mppt), but for now, it can be calculated ignoring mppt)

consumes - sun, weather

Sun --> Weather --> PV = X Joules

We need to simulate a grid provider

properties

- on/off

produces

- on/off
- Joules

consumes - none

We need to simulate an inverter (this will need a lot more work in future)

properties

- size
- min/maxes (not important now)
- losses

produces - Joules

consumes - Joules

we need to simulate an oven

properties

- power requirements

produces

- on/off
- Joules

Some kind of UI to do basic management

some kind of "watcher" to see how things are flowing

The inverter would listen for consumption and production events, and calculate the nett Joules, and emit counteracting Joules to satisfy the equation. This results in your input/output energy matrix. A dashboard can then display the decision which results in the flow

We then also need some kind of persistence for reporting, so something that sees all the events and ties them up.

Switching equipment on or off is simply a matter of scaling the deployments, their events would disappear, thus their "need" or ability to produce as well.

Busy learning angular

https://www.youtube.com/watch?v=NMzl2pGOK_8&list=PL1BztTYDF-QNrtkvjkT6Wjc8es7QB4Gty&index=1
