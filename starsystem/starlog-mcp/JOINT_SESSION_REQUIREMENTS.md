# Joint Session Requirements — Isaac Apr 02 2026

## Isaac's Words (verbatim)

"so the fix is to make the starlog system have a joint session type which it can join event streams into a higher order starlog automatically for you, and these are implicit to you but it returns the ID for the starsystem you are in automatically. YES. So, basically you say this update has to do with list these paths or starsystems, it resolves which starsystems those belong to at the top level below seed ship, and then it puts them in *that* starlog (the one that is addressed as the list, and then caps it with a name) and returns the ID to you "you should be in this starlog." its not necessarily 1:1 with starsystems. Its a hyperedge? Every starsystem HAS ITS OWN starlog *BUT* starlogs exist *from anywhere you make an observation in the entire galaxy*. ID can be changed."

## The Problem (Isaac's words)

"BECAUSE A STARSYSTEM IS A FUCKING DIRECTORY YOU ARE GETTING FUCKING CONFUSED ABOUT WHERE TO FUCKING PUT INFORMATION WHEN IT SPANS TWO SYSTEMS OR MORE"

## Context

"i think the core issue might be starlog itself. it might be that starlog is too confusing in terms of when you are working in the monorepo it isnt clear where to put every diary update because its not one codebase its like 40. So maybe you need to know that starlog can be used with the monorepo dir starsystem itself or with any of the starsystems inside of it... and maybe we just need to look at decoupling starlog from dirs, it should just be like 'starlog partof starsystem' so then debug diary update on starlog's session xyz can happen in any given starsystem or in seed ship... i think that might actually be the problem with the geometry, as weirdly specific as that is, i think its the major reason why everything is wonky. you just adding concepts in carton or DB isnt always the right way to do it. We might have to unify a lot of these things with starlog, and make starlog like the event ledger of the starsystem so not everything is a debug diary update but on the backend basically yeah, everything going into carton for a starsystem is happening *as* a starlog debug event in the diary of a session. That might be a missing piece here."

## Additional Context

"ok but i was going to say actually that i think the core issue might be starlog itself... also you need to ensure that the OWL schema DOES INCLUDE more specific restrictions than the models because that is the whole fucking point of it. CODE CANNOT FUCKING SPECIFY INTO ARBITRARY STRING WITHOUT TEMPLATES, BUT IT DOESNT MATTER IF ITS TEMPLATES EXIST BECAUSE THEN YOU NEED A LOGIC ENGINE TO GO BETWEEN THEM. WE ARE BUILDING ALL THE PARTS WE NEED FOR THE LOGIC ENGINE RIGHT NOW."

## Starlog Layers (Isaac Apr 02)

"there is the carton reflection of starlog and then there is 'how starlog base works'. Starlog base was made on filesystem. Now, starlog tools trigger starlog carton and starlog base. We need starlog carton to be better, and we might have to change starlog base to accommodate that."

"A starlog requires all that stuff, but we KNOW how to generate everything required if you are referring to two actual starsystems. We can just be like 'this starlog is about x & y' etc..."

## Dragonbones → Starlog Link (Isaac Apr 02)

Bug types (and all Dragonbones entity chains: Bug_, Design_, Idea_, Inclusion_Map_) should be part_of starlogs. They happen DURING sessions — they should be linked to the session they occurred in. This gives temporal context: when was this bug found, during which session, what else was happening.

## OMNISANC Zone → Starlog Routing (Isaac Apr 02)

OMNISANC zones map to starlog sessions:
- HOME → Seed Ship starlog
- STARPORT → starport starlog
- JOURNEY → starsystem starlog
- MISSION CONTROL → mission starlog
- LANDING → landing starsystem starlog

OMNISANC already knows where you are. It just doesn't route to starlog yet. The zone IS the answer to "which starlog does this event belong to."

## The Two Primary Tools (Isaac Apr 02)

"dragonbones gives you instant access to carton with low token count and debug diary gives you instant access to the event ledger for that exact thing you are working on"

- Dragonbones → CartON (the graph, structural)
- Debug diary → Starlog (the ledger, temporal)

## The Core UX Change (Isaac Apr 02)

"the diary can be used any time, and depending on if you have session started already or not it just figures out where it goes"

Debug diary auto-routes based on what you're working on. No explicit session management needed. No "start_starlog first" errors. You write a diary entry, it lands in the right place based on OMNISANC zone / active starsystem / whatever you're touching.

"we are just making the starlog system more geometrically amenable to that traversal we need to do for archaeology sometimes (which happens to make it way easier to use overall too because the ux is different in this way we are talking about)"
