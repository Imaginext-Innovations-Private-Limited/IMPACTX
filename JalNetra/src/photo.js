import { crc32, deflateSync } from 'node:zlib';

export const maxDimension = 1200;
export const maxRgbBytes = maxDimension ** 2 * 3;

function chunk(type, data) {
  const name = Buffer.from(type, 'ascii');
  const packet = Buffer.alloc(data.length + 12);
  packet.writeUInt32BE(data.length);
  name.copy(packet, 4);
  data.copy(packet, 8);
  packet.writeUInt32BE(crc32(packet.subarray(4, -4)), packet.length - 4);
  return packet;
}

export function encodePhoto(width, height, pixels) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 2; // Eight-bit RGB.

  const rowBytes = width * 3;
  const rows = Buffer.alloc((rowBytes + 1) * height);
  for (let row = 0; row < height; row++) {
    // Filter type 0 precedes each row.
    pixels.copy(rows, row * (rowBytes + 1) + 1, row * rowBytes, (row + 1) * rowBytes);
  }

  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', header),
    chunk('IDAT', deflateSync(rows)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}
