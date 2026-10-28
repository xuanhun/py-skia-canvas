// Official pinned Node runtime Number formatting, exact IEEE bit-pattern inputs.
import fs from'node:fs';let[input,out]=process.argv.slice(2),values=JSON.parse(fs.readFileSync(input));let strings=values.map(h=>{let b=Buffer.from(h,'hex');return b.readDoubleBE().toString();});fs.writeFileSync(out,JSON.stringify({node:process.version,strings})+'\n');
