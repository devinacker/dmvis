dmvis - Doom map visualizer
by Revenant

dmvis is a Python (2.7) script to make animated GIFs out of Doom engine levels.

The GIFs are drawn by iterating over a map's linedefs in numerical order, while also tracing out adjacent lindedefs in the same sector. The idea is to try to provide a "start-to-finish" view of a map's construction.

The result isn't usually perfectly chronological, since areas being deleted/reworked/detailed, etc. can cause things to sometimes show up incomplete or slightly out-of-order - but it can still give a pretty interesting look at the process behind a lot of the original map designs.

This script uses the "omgifol" library by Fredrik Johansson to load maps. The original library is available at http://omgifol.sourceforge.net.

If you want support for Hexen and ZDoom maps, you can use my personal fork, located here: https://github.com/devinacker/omgifol

(Note: Both versions of the library only support maps named ExMx or MAPxx currently.)