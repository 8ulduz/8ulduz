const {test}=require('node:test');
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const stats=import(pathToFileURL(path.join(__dirname,'../assets/source-stats.js')));
const reader=import(pathToFileURL(path.join(__dirname,'../assets/reader.js')));
test('source count periods use Baku midnight, Monday week and calendar month/year',async()=>{
  const {periodStarts}=await stats;
  assert.deepEqual(periodStarts(new Date('2026-10-31T21:00:00Z')),['2026-11-01','2026-10-26','2026-11-01','2026-01-01']);
  assert.deepEqual(periodStarts(new Date('2027-01-03T21:00:00Z')),['2027-01-04','2027-01-04','2027-01-01','2027-01-01']);
});
test('source counts are read from the global service; unavailable is not zero',async()=>{
  const {fetchCounts,countText,eventPath}=await stats;let calls=0;
  const values=await fetchCounts('vm6666','AZƏRTAC',async url=>{assert.ok(url.includes(encodeURIComponent(eventPath('AZƏRTAC'))));const i=calls++;return {ok:i!==2,json:async()=>({count:['10','1,000','','5,000'][i]})};});
  assert.equal(countText(values),'10/1000/—/5000');
  assert.equal(countText(),'—/—/—/—');
});
test('article audio chunks preserve words and do not truncate long stories',async()=>{
  const {readingChunks}=await reader;
  const text=Array.from({length:500},(_,i)=>'söz'+i).join(' ')+'. Son cümlə!';
  const chunks=readingChunks(text);
  assert.ok(chunks.every(c=>c.length<=220));
  assert.equal(chunks.join(' '),text);
});
