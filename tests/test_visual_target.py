import base64,io
import pytest
np=pytest.importorskip('numpy');Image=pytest.importorskip('PIL.Image')
from bokkio.visual_target import match_image

def png(a):
 stream=io.BytesIO();Image.fromarray(a.astype('uint8')).save(stream,format='PNG');return stream.getvalue()

def test_moved_distinctive_image_anchor():
 rng=np.random.default_rng(42);template=rng.integers(0,255,(24,40),dtype='uint8');image=np.full((160,220),190,dtype='uint8');image[70:94,120:160]=template
 result=match_image(png(image),{'png':base64.b64encode(png(template)).decode()})
 assert result['score']>.99 and result['x']==140 and result['y']==82

def test_duplicate_and_flat_image_refuse():
 rng=np.random.default_rng(42);template=rng.integers(0,255,(24,40),dtype='uint8');image=np.full((180,240),190,dtype='uint8');image[20:44,20:60]=template;image[110:134,140:180]=template
 with pytest.raises(ValueError,match='multiple'):match_image(png(image),{'png':base64.b64encode(png(template)).decode()})
 with pytest.raises(ValueError):match_image(png(image),{'png':base64.b64encode(png(np.full((20,20),190))).decode()})
