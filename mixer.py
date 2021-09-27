#PyJ2D - Copyright (C) 2011 James Garnon <https://gatc.ca/>
#Released under the MIT License <https://opensource.org/licenses/MIT>

from javax.sound.sampled import AudioSystem, AudioFormat
from javax.sound.sampled import LineUnavailableException
from java.io import File, IOException
from java.lang import Thread, Runnable, InterruptedException, IllegalArgumentException
from java.util.concurrent import ConcurrentLinkedDeque
from java.util import NoSuchElementException
from java.util.concurrent.atomic import AtomicBoolean
import jarray
from pyj2d import env
try:
    from pyj2d import Mixer as AudioMixer
except ImportError:
    AudioMixer = None

__docformat__ = 'restructuredtext'


class Mixer(Runnable):
    """
    **pyj2d.mixer**
    
    * pyj2d.mixer.init
    * pyj2d.mixer.quit
    * pyj2d.mixer.get_init
    * pyj2d.mixer.stop
    * pyj2d.mixer.pause
    * pyj2d.mixer.unpause
    * pyj2d.mixer.set_num_channels
    * pyj2d.mixer.get_num_channels
    * pyj2d.mixer.set_reserved
    * pyj2d.mixer.find_channel
    * pyj2d.mixer.get_busy
    * pyj2d.mixer.Sound
    * pyj2d.mixer.Channel
    * pyj2d.mixer.music
    """

    def __init__(self):
        self._mixer = None
        Sound._mixer = self
        Channel._mixer = self
        self.Sound = Sound
        self.Channel = self._get_channel
        self.music = None
        self._channel_max = 8
        self._channels = {}
        self._channel_available = ConcurrentLinkedDeque()
        self._channel_available.addAll(list(range(self._channel_max)))
        self._channel_active = ConcurrentLinkedDeque()
        self._channel_reserved = ConcurrentLinkedDeque()
        self._channel_reserved_num = 0
        self._thread = None
        self._active = AtomicBoolean(False)
        self._initialized = False
        self._nonimplemented_methods()

    def init(self, frequency=22050, size=-16, channels=2, buffer=4096):
        """
        Mixer initialization.
        Argument sampled frequency, bit size, channels, and buffer.
        Currently implements PCM 16-bit audio.
        Plays WAV, AIFF, and AU sampled audio.
        To specify BigEndian format of AIFF and AU, use size of float type.
        The mixing is done by Mixer.class, compiled with 'javac Mixer.java'.
        For JAR creation include with 'jar uvf App.jar pyj2d/Mixer.class'.
        """
        if not self._initialized:
            encoding = {True:AudioFormat.Encoding.PCM_SIGNED, False:AudioFormat.Encoding.PCM_UNSIGNED}[size<0]
            channels = {True:1, False:2}[channels<=1]
            framesize = int((abs(size)/8) * channels)
            isBigEndian = isinstance(size, float)
            self._audio_format = AudioFormat(encoding, int(frequency), int(abs(size)), channels, framesize, int(frequency), isBigEndian)
            self._bufferSize = buffer
            try:
                self._mixer = AudioMixer(self._audio_format, self._bufferSize)
            except TypeError:
                self._mixer = None
                return None
            if not self._mixer.isInitialized():
                return None
            self._bufferSize = self._mixer.getBufferSize()
            self._byteArray = jarray.zeros(self._bufferSize, 'b')
            self.music = Music()
            self._initialized = True
            self._thread = Thread(self)
            self._thread.start()
        return None

    def pre_init(self, frequency=22050, size=-16, channels=2, buffer=4096):
        """
        Mixer initialization.
        """
        self.init(frequency, size, channels, buffer)
        return None

    def quit(self):
        """
        Stop mixer processing and release resources.
        """
        self._initialized = False
        return None

    def _quit(self):
        self.stop()
        self.music._channel.stop()
        try:
            self._mixer.quit()
        except AttributeError:
            pass
        self._mixer = None

    def get_init(self):
        """
        Get the audio format initialized.
        """
        if self._initialized:
            frequency = int(self._audio_format.sampleRate)
            format = self._audio_format.sampleSizeInBits * {True:1,False:-1}[self._audio_format.bigEndian]
            channels = self._audio_format.channels
            return (frequency, format, channels)
        else:
            return None

    def stop(self):
        """
        Stop mixer channels.
        """
        for id in self._channel_active.iterator():
            if id > -1:
                self._channels[id].stop()
        return None

    def pause(self):
        """
        Pause mixer channels.
        """
        for id in self._channel_active.iterator():
            if id > -1:
                self._channels[id].pause()
        return None

    def unpause(self):
        """
        Unpause mixer channels.
        """
        for id in self._channel_active.iterator():
            if id > -1:
                self._channels[id].unpause()
        return None

    def set_num_channels(self, count):
        """
        Set maximum mixer channels.
        Argument channel count.
        """
        if count >= self._channel_max:
            for id in range(self._channel_max, count):
                self._channel_available.add(id)
            self._channel_max = count
        elif count >= 0:
            for id in range(count, self._channel_max):
                if id in self._channels:
                    if self._channels[id] is not None:
                        self._channels[id].stop()
                    del self._channels[id]
                self._channel_available.remove(id)
            self._channel_max = count
        return None

    def get_num_channels(self):
        """
        Get maximum mixer channels.
        """
        return self._channel_max

    def set_reserved(self, count):
        """
        Reserve channel.
        Argument reserved channel count.
        """
        if count > self._channel_max:
            count = self._channel_max
        elif count < 0:
            count = 0
        self._channel_reserved_num = count
        self._channel_reserved.clear()
        for id in range(self._channel_reserved_num):
            self._channel_reserved.add(id)
            self._channel_available.remove(id)
        return None

    def find_channel(self, force=False):
        """
        Get an inactive mixer channel.
        Optional force attribute return longest running channel if all active.
        """
        try:
            id = self._channel_available.pop()
            self._channel_available.add(id)
            return self._get_channel(id)
        except NoSuchElementException:
            pass
        try:
            if self._channel_reserved_num:
                id = self._channel_reserved.pop()
                self._channel_reserved.add(id)
                return self._get_channel(id)
        except NoSuchElementException:
            pass
        if not force:
            return None
        longest = None
        longest_reserved = None
        for id in self._channel_active.iterator():
            if id > self._channel_reserved_num-1:
                longest = id
                break
            elif id > -1:
                if longest_reserved is None:
                    longest_reserved = id
        if longest is not None:
            channel = longest
        else:
            if longest_reserved is not None:
                channel = longest_reserved
            else:
                channel = 0
        channel = self._get_channel(channel)
        return channel

    def _retrieve_channel(self):
        try:
            id = self._channel_available.pop()
            channel = self._get_channel(id)
            self._channel_active.add(id)
            self._active.set(True)
        except NoSuchElementException:
            channel = None
        return channel

    def get_busy(self):
        """
        Check if mixer channels are actively processing.
        """
        for id in self._channel_active.iterator():
            if id > -1:
                if self._channels[id]._active:
                    return True
        return False

    def run(self):
        while self._initialized:
            if not self._active.get():
                self._thread_sleep()
                continue
            if self._channel_active.size() > 1:
                data, data_len = self._mix(self._channel_active)
                if data_len > 0:
                    self._write(data, data_len)
            else:
                try:
                    channel = self._channel_active.getFirst()
                    data, data_len = self._read(channel)
                except NoSuchElementException:
                    data_len = 0
                if data_len > 0:
                    self._write(data, data_len)
        self._quit()

    def _thread_sleep(self):
        try:
            self._thread.sleep(10)
        except InterruptedException:
            Thread.currentThread().interrupt()
            self.quit()

    def _mix(self, channels):
        for id in channels.iterator():
            channel = self._channels[id]
            if not channel._active.get():
                continue
            try:
                data, data_len, lvol, rvol = channel._get()
            except AttributeError:
                continue
            self._mixer.setAudioData(data, data_len, lvol, rvol)
        data_len = self._mixer.getAudioData(self._byteArray)
        return self._byteArray, data_len

    def _read(self, channel):
        channel = self._channels[channel]
        if not channel._active.get():
            data, data_len = None, 0
        else:
            try:
                data, data_len, lvol, rvol = channel._get()
            except AttributeError:
                data, data_len = None, 0
        if data_len:
            if lvol < 1.0 or rvol < 1.0:
                data = self._mixer.processVolume(data, data_len, lvol, rvol)
        return data, data_len

    def _write(self, data, data_len):
        try:
            self._mixer.write(data, 0, data_len)
        except IllegalArgumentException:
            nonIntegralByte = data_len % self._audio_format.getFrameSize()
            if nonIntegralByte:
                data_len -= nonIntegralByte
                try:
                    self._mixer.write(data, 0, data_len)
                except (IllegalArgumentException, LineUnavailableException):
                    pass
        except LineUnavailableException:
            pass

    def _activate_channel(self, id):
        if id > self._channel_reserved_num-1:
            self._channel_available.remove(id)
        else:
            self._channel_reserved.remove(id)
        self._channel_active.add(id)
        self._active.set(True)

    def _deactivate_channel(self, id):
        self._channel_active.remove(id)
        if self._channel_active.isEmpty():
            self._active.set(False)

    def _restore_channel(self, id):
        if id > self._channel_reserved_num-1:
            self._channel_available.add(id)
        elif id > -1:
            self._channel_reserved.add(id)

    def _get_channel(self, id):
        try:
            return self._channels[id]
        except KeyError:
            return Channel(id)

    def _register_channel(self, channel):
        id = channel._id
        if id < self._channel_max:
            self._channels[id] = channel
        else:
            raise AttributeError("Channel not available.")

    def _nonimplemented_methods(self):
        self.fadeout = lambda *arg: None


class Sound(object):
    """
    **pyj2d.mixer.Sound**
    
    * Sound.play
    * Sound.stop
    * Sound.set_volume
    * Sound.get_volume
    * Sound.get_num_channels
    * Sound.get_length
    """

    _id = 0
    _mixer = None

    def __init__(self, sound_file):
        self._id = Sound._id
        Sound._id += 1
        if isinstance(sound_file, str):
            try:
                self._sound_object = env.japplet.getClass().getResource(sound_file.replace('\\','/'))    #java uses /, not os.path Windows \
                if not self._sound_object:
                    raise IOError
            except:
                self._sound_object = File(sound_file)      #make path os independent
        else:
            self._sound_object = sound_file
        self._channel = None
        self._volume = 1.0
        self._nonimplemented_methods()

    def play(self, loops=0, maxtime=0, fade_ms=0):
        """
        Play sound on mixer channel.
        Argument loops is number of repeats or -1 for continuous.
        """
        self._channel = self._mixer._retrieve_channel()
        try:
            self._channel._play(self, loops)
        except AttributeError:
            pass
        return self._channel

    def stop(self):
        """
        Stop sound on active channels.
        """
        channels = self._mixer._channels
        for id in self._mixer._channel_active.iterator():
            if id > -1:
                try:
                    if channels[id]._sound._id == self._id:
                        channels[id].stop()
                except AttributeError:
                    continue
        return None

    def set_volume(self, volume):
        """
        Set sound volume.
        Argument volume of value 0.0 to 1.0.
        """
        if volume < 0.0:
            volume = 0.0
        elif volume > 1.0:
            volume = 1.0
        self._volume = volume
        return None

    def get_volume(self):
        """
        Get sound volume.
        """
        return self._volume

    def get_num_channels(self):
        """
        Get number of channels sound is active.
        """
        channels = self._mixer._channels
        channel = 0
        for id in self._mixer._channel_active.iterator():
            if id > -1:
                try:
                    if channels[id]._sound._id == self._id:
                        channel += 1
                except AttributeError:
                    continue
        return channel

    def get_length(self):
        """
        Get length of sound sample.
        """
        stream = AudioSystem.getAudioInputStream(self._sound_object)
        length = stream.getFrameLength() / stream.getFormat().getFrameRate()
        stream.close()
        return length

    def _nonimplemented_methods(self):
        self.fadeout = lambda *arg: None
        self.get_buffer = lambda *arg: None


class Channel(object):
    """
    **pyj2d.mixer.Channel**
    
    * Channel.play
    * Channel.stop
    * Channel.pause
    * Channel.unpause
    * Channel.set_volume
    * Channel.get_volume
    * Channel.get_busy
    * Channel.get_sound
    """

    _mixer = None

    def __init__(self, id):
        self._id = id
        self._sound = None
        self._stream = None
        self._data = jarray.zeros(self._mixer._bufferSize, 'b')
        self._data_len = 0
        self._active = AtomicBoolean(False)
        self._pause = False
        self._loops = 0
        self._volume = 1.0
        self._lvolume = 1.0
        self._rvolume = 1.0
        self._mixer._register_channel(self)
        self._nonimplemented_methods()

    def _set_sound(self, sound):
        self._sound = sound
        self._stream = AudioSystem.getAudioInputStream(sound._sound_object)

    def _get(self):
        try:
            self._data_len = self._stream.read(self._data)
        except IOException:
            self._data_len = 0
        if self._data_len > 0:
            return (self._data, self._data_len, self._lvolume*self._sound._volume, self._rvolume*self._sound._volume)
        else:
            if not self._loops:
                self.stop()
            else:
                self._stream.close()
                self._set_sound(self._sound)
                self._loops -= 1
            return (self._data, self._data_len, 1.0, 1.0)

    def _play(self, sound, loops):
        self._set_sound(sound)
        self._loops = loops
        self._active.set(True)

    def play(self, sound, loops=0, maxtime=0, fade_ms=0):
        """
        Play sound on channel.
        Argument sound to play and loops is number of repeats or -1 for continuous.
        """
        if self._sound:
            lv, rv = self._lvolume, self._rvolume
            self.stop()
            self.set_volume(lv, rv)
        self._set_sound(sound)
        self._loops = loops
        self._active.set(True)
        self._mixer._activate_channel(self._id)
        return None

    def stop(self):
        """
        Stop sound on channel.
        """
        if not self._active.get():
            return None
        self._active.set(False)
        self._mixer._deactivate_channel(self._id)
        try:
            self._stream.close()
            self._stream = None
        except AttributeError:
            pass
        self._sound = None
        self._pause = False
        self._loops = 0
        self._volume = 1.0
        self._lvolume = 1.0
        self._rvolume = 1.0
        self._mixer._restore_channel(self._id)
        return None

    def pause(self):
        """
        Pause sound on channel.
        """
        if self._active.get():
            self._active.set(False)
            self._pause = True
        return None

    def unpause(self):
        """
        Unpause sound on channel.
        """
        if self._pause:
            self._active.set(True)
            self._pause = False
        return None

    def set_volume(self, volume, volume2=None):
        """
        Set channel volume of sound playing.
        Argument volume of value 0.0 to 1.0, setting for both speakers when single, stereo l/r speakers with second value.
        """
        if volume < 0.0:
            volume = 0.0
        elif volume > 1.0:
            volume = 1.0
        self._lvolume = volume
        if volume2:
            if volume2 < 0.0:
                volume2 = 0.0
            elif volume2 > 1.0:
                volume2 = 1.0
            self._rvolume = volume2
        else:
            self._rvolume = self._lvolume
            self._volume = volume
        return None

    def get_volume(self):
        """
        Get channel volume for current sound.
        """
        return self._volume

    def get_busy(self):
        """
        Check if channel is processing sound.
        """
        return self._active.get()

    def get_sound(self):
        """
        Get sound open by channel.
        """
        return self._sound

    def _nonimplemented_methods(self):
        self.fadeout = lambda *arg: None
        self.queue = lambda *arg: None
        self.get_queue = lambda *arg: None
        self.set_endevent = lambda *arg: None
        self.get_endevent = lambda *arg: 0


class Music(object):
    """
    **pyj2d.mixer.music**

    * music.load
    * music.unload
    * music.play
    * music.stop
    * music.pause
    * music.unpause
    * music.set_volume
    * music.get_volume
    * music.get_busy
    """

    def __init__(self):
        self._channel = Channel(-1)
        self._sound = None

    def load(self, sound_file):
        """
        Load music file.
        """
        self._sound = Sound(sound_file)
        return None

    def unload(self):
        """
        Unload music file.
        """
        self._channel.stop()
        self._sound = None
        return None

    def play(self, loops=0, maxtime=0, fade_ms=0):
        """
        Play music.
        Argument loops is number of repeats or -1 for continuous.
        """
        self._channel.play(self._sound, loops)
        return None

    def stop(self):
        """
        Stop music.
        """
        self._channel.stop()
        return None

    def pause(self):
        """
        Pause music.
        """
        self._channel.pause()
        return None

    def unpause(self):
        """
        Unpause music.
        """
        self._channel.unpause()
        return None

    def set_volume(self, volume):
        """
        Set music volume.
        Argument volume of value 0.0 to 1.0.
        """
        self._sound.set_volume(volume)
        return None

    def get_volume(self):
        """
        Get volume for current music.
        """
        return self._sound.get_volume()

    def get_busy(self):
        """
        Check if music playing.
        """
        return self._channel.get_busy()

