const maxPhotoBytes = 5 * 1024 * 1024;

async function decodePhoto(photo) {
  if (photo.size > maxPhotoBytes) throw new Error('Choose a photo smaller than 5 MB.');
  const signature = new Uint8Array(await photo.slice(0, 8).arrayBuffer());
  const png = [137, 80, 78, 71, 13, 10, 26, 10].every((byte, index) => signature[index] === byte);
  const jpeg = signature[0] === 255 && signature[1] === 216 && signature[2] === 255;
  if (!png && !jpeg) throw new Error('Choose a valid JPEG or PNG.');
  try {
    return await createImageBitmap(photo);
  } catch {
    throw new Error('The photo could not be read. Try a different JPEG or PNG.');
  }
}

export async function normalize(file) {
  const image = await decodePhoto(file);
  try {
    const scale = Math.min(1, 1200 / Math.max(image.width, image.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(image.width * scale));
    canvas.height = Math.max(1, Math.round(image.height * scale));
    const ctx = canvas.getContext('2d', { alpha: false, willReadFrequently: true });
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    const rgba = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    const rgb = new Uint8Array(canvas.width * canvas.height * 3);
    for (let source = 0, target = 0; source < rgba.length; source += 4, target += 3) {
      rgb[target] = rgba[source];
      rgb[target + 1] = rgba[source + 1];
      rgb[target + 2] = rgba[source + 2];
    }
    return { width: canvas.width, height: canvas.height, pixels: new Blob([rgb], { type: 'application/octet-stream' }) };
  } finally {
    image.close();
  }
}
