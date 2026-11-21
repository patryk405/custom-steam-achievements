import botwCover from './covers/botw.jpg?url';
import ootCover from './covers/oot.png?url';
import bloodborneCover from './covers/bloodborne.jpg?url';
import arceusCover from './covers/arceus.png?url';
import odysseyCover from './covers/odyssey.png?url';
import pokopiaCover from './covers/pokopia.jpg?url';
export const games = [
  {id:'botw',title:'The Legend of Zelda: Breath of the Wild',short:'Breath of the Wild',cover:botwCover,source:"https://en.wikipedia.org/wiki/The_Legend_of_Zelda%3A_Breath_of_the_Wild",tracker:'Savage Wind',supported:true,artNote:'Original game cover'},
  {id:'oot',title:'The Legend of Zelda: Ocarina of Time Remake',short:'Ocarina of Time Remake',cover:ootCover,source:"https://www.steamgriddb.com/grid/787839",tracker:'Longshot 3.0.0 · 66 objectives',supported:true,artNote:'Ocarina of Time artwork by ABH20 on SteamGridDB'},
  {id:'bloodborne',title:'Bloodborne',short:'Bloodborne',cover:bloodborneCover,source:"https://www.doesitplay.org/game/Bloodborne/ps4/Base%20PS4?region=ESRB&version=Standard",tracker:'BBPort · 40 trophies · experimental',supported:false,artNote:'Original game cover'},
  {id:'arceus',title:'Pokémon Legends: Arceus',short:'Pokémon Legends: Arceus',cover:arceusCover,source:"https://www.gamesaver.com.au/game/pokemon-legends-arceus",tracker:'PokeL-ARecomp · saves · experimental',supported:false,artNote:'Original game cover'},
  {id:'odyssey',title:'Super Mario Odyssey',short:'Super Mario Odyssey',cover:odysseyCover,source:"https://www.steamgriddb.com/game/5245268",tracker:'Super Odyssey PC · saves · experimental',supported:false,artNote:'Original game cover'},
  {id:'pokopia',title:'Pokémon Pokopia',short:'Pokémon Pokopia',cover:pokopiaCover,source:"https://backloggd.com/games/pokemon-pokopia/",tracker:'Recompia · direct saves · experimental',supported:false,artNote:'Original game cover'},
] as const;
export type GameId = typeof games[number]['id'];
