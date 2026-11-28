import test from 'node:test';
import assert from 'node:assert/strict';
import { communityAdvice } from '../public/community.js';
test('unknown and clear observations never establish safety', () => {
  for (const signals of [[], [{state:'clear',category:'foam'}]]) {
    const result = communityAdvice(signals);
    assert.equal(result.active,0);
    assert.match(result.advice[0],/does not establish safe water/);
  }
});
test('pending and verified concerns produce category-specific precautions', () => {
  const result = communityAdvice([{state:'pending',category:'foam'},{state:'verified',category:'dumping'}]);
  assert.equal(result.active,2);
  assert.equal(result.verified,1);
  assert.match(result.advice.join(' '),/Avoid direct contact/);
  assert.match(result.advice.join(' '),/authorised dry-land cleanups/);
});
