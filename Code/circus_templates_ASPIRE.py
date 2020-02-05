import matplotlib.pyplot as plt

class NoStdStreams(object):
    
    def __init__(self,stdout = None, stderr = None):
        import sys, os
        self.devnull = open(os.devnull,'w')
        self._stdout = stdout or self.devnull or sys.stdout
        self._stderr = stderr or self.devnull or sys.stderr
    def __enter__(self):
        import sys
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush(); self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr
    def __exit__(self, exc_type, exc_value, traceback):
        import sys
        self._stdout.flush(); self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.devnull.close()
           
class Templates:
    """ Here we read templates from the folder and create plots for them"""

    def __init__(self, directory, case, fif_file, params, sensors='grad', n_sp=100, cc_merge=0.9, cut_off=9,cut_off_top=200, N_t=80, MAD=6.0):
        """ Set parameters to open
        the folder with Syking Circus results   
        """
        import os
        import traceback
        #from circus.shared.parser import CircusParser
        
        self.case = case
        self.case_dir = directory
        self.sensors = sensors
        self.n_sp = n_sp
        self.folder = '%sSpyking_circus/%s_%s/'%(self.case_dir, self.case, fif_file[:-4])
        output_dir = 'cut_off_(%s,%s)_MAD_%s_N_t_%s_cc_merge_%s_%s'%(cut_off,cut_off_top, MAD, N_t, cc_merge, sensors)
        self.filename = '%s_0.npy'%fif_file[:-4]
        self.params = params#CircusParser('%s/%s/%s'%(self.folder, output_dir, self.filename))
        
        self.spike_thresh = float(self.params.get('detection','spike_thresh'))
        self.N_t = self.params.getint('detection','N_t')
        self.cut_off = 0.1 #int(self.params.get('filtering','cut_off')[0])
        self.cut_off_top = cut_off_top
        self.cc_merge = float(self.params.get('clustering','cc_merge'))
        self.output_dir = 'cut_off_(%s,%s)_MAD_%s_N_t_%s_cc_merge_%s_%s'%(self.cut_off,self.cut_off_top, self.spike_thresh, self.N_t, self.cc_merge, self.sensors)
        
        try:
            os.makedirs('%s%s/Templates_plots'%(self.folder, self.output_dir),exist_ok=True)
            os.makedirs('%s%s/Templates_waveforms'%(self.folder, self.output_dir),exist_ok=True)
            os.makedirs('%s%s/SVG_plots'%(self.folder, self.output_dir),exist_ok=True)
            self.png_path = '%s%s/Templates_plots/'%(self.folder, self.output_dir)
            self.waveforms_path = '%s%s/Templates_waveforms'%(self.folder, self.output_dir)
            self.svg_path = '%s%s/SVG_plots/'%(self.folder, self.output_dir)
        except Exception: traceback.print_exc() #print('Wrong path!')
        Templates.read_templates(self)
        
    def read_templates(self):
        """ Here we read templates from the folder"""
        import pandas as pd
        import numpy as np
        self.templates = pd.read_excel('%s%s/Results/Templates_%s_all.xlsx'%(self.folder, self.output_dir, self.case))
        self.templates['Time'] = self.templates['Spiketimes']
        #self.templates = self.templates[abs(self.templates.Amplitudes-1)<0.5].reset_index(drop=True).copy()
        self.main_temp_names = np.unique(self.templates['Template'].value_counts()[self.templates['Template'].value_counts()>=self.n_sp].index.tolist())
        
    def all_temp_barplot(self, name=''):
        """ Here we plot barplot for all templates"""
        title = "Number of spikes for each template"
        fig = self.templates['Template'].value_counts()[self.templates['Template'].value_counts() >= self.n_sp].plot(kind="bar", title=title, figsize=(8,9))
        fig.axes.set_ylabel("Spikes")
        fig.axes.set_xlabel("Templates")
        fname = "%sall_templates_barplot_%s.png"%(self.png_path, name)
        plt.savefig(fname, dpi=200)
        plt.clf()
        plt.close()
    
    def best_spikes_temp_n(self, template):
        """ Here we selecte best spikes for one template"""
        import numpy as np
        
        self.template = template
        self.temp_n = int(self.template.split('_')[1])
        self.templates_n = self.templates[self.templates.Template == self.template]
        self.templates_n.reset_index(drop=True, inplace=True)
        self.n_spikes = len(self.templates_n)
        #self.templates_n.Amplitudes = np.abs(self.templates_n.Amplitudes - 1)
        #self.best_temp = self.templates_n.sort_values('Amplitudes').reset_index(drop=True).loc[0:200].copy()
        self.best_temp = self.templates_n[abs(self.templates_n.Amplitudes-1)<0.5].reset_index(drop=True).loc[0:200].copy()
        #sel_peacks = [True if abs((self.best_temp.Spiketimes[i]-500)/1000-int((self.best_temp.Spiketimes[i]-500)/1000))<0.3 else False for i in range(len(self.best_temp.Spiketimes))]
        #self.best_temp = self.best_temp[sel_peacks].reset_index(drop=True).copy()
        self.best_temp = self.best_temp.sort_values('Spiketimes').reset_index(drop=True).copy()
        #self.best_temp['Amplitudes'] = self.best_temp['Amplitudes'] + 1
    
    def create_epochs_temp_n(self, epochs, picks_raw=True):
        """ Here we create epochs for template n"""
        import mne
        import numpy as np

        self.data_info = epochs.info
        n_spikes_all = len(epochs)
        best_best = self.best_temp[abs(self.best_temp.Amplitudes-1)<0.5]
        times = self.best_temp.Spiketimes.tolist()
        round_det = [round((i-500)/1000) for i in times]

        #self.selections_time = dict(zip([(i/1000-500)-int(i/1000-500) for i in times], ))
        selections = [True if i in round_det else False for i in range(n_spikes_all)]
        self.vlines = [(times[round_det.index(i)]-500)/1000-i for i in range(n_spikes_all) if i in round_det]
        self.epochs_temp = epochs[selections]
        self.epochs_temp.load_data()
        epochs_0 = epochs[0]
        epochs_0.load_data()
        self.data_info_sens = epochs_0.pick_types(meg=self.sensors, eeg=False,stim=False, eog=False).info
        del epochs_0

        #eve_id = self.temp_n+1
        #eve_name = self.template
        #
        #raw_filt.load_data()
        #self.data_info = raw_filt.pick_types(meg=True, eeg=False,stim=False, eog=False).info
        ##channel_indices_by_type = mne.io.pick.channel_indices_by_type(raw_filt.info)
        #
        #new_events, eve = [], []
        #first_samp = raw_filt.first_samp

        #for spike_time in self.best_temp['Spiketimes']: #self.templates_n['Spiketimes']:
        #    eve = [int(round(spike_time + first_samp)), 0, eve_id]
        #    new_events.append(eve)

        #if 'STI_sp' not in raw_filt.info['ch_names']:
        #    stim_data = np.zeros((1, len(raw_filt.times)))
        #    info_sp = mne.create_info(['STI_sp'], raw_filt.info['sfreq'], ['stim'])
        #    stim_sp = mne.io.RawArray(stim_data, info_sp, verbose=False)
        #    raw_filt.add_channels([stim_sp], force_update_info=True)

        #raw_filt.add_events(new_events, stim_channel='STI_sp', replace=True)
        #self.events_temp = mne.find_events(raw_filt, stim_channel='STI_sp', verbose=False)
        #event_id = {eve_name: eve_id}
        #picks = mne.pick_types(raw_filt.info, meg=picks_raw, eeg=False, eog=False)
        #self.epochs_temp = mne.Epochs(raw_filt, self.events_temp, event_id,  tmin, tmax, baseline=None, picks=picks, preload=True, verbose=False)
        #self.data_info_sens = raw_filt.pick_types(meg=self.sensors, eeg=False,stim=False, eog=False).info
        #del raw_filt, picks, event_id
    
    def largest_indices(ary, n):
        """ Returns the n largest indices from a numpy array."""
        import numpy as np
        flat = ary.flatten()
        indices = np.argpartition(flat, -n)[-n:]
        indices = indices[np.argsort(-flat[indices])]
        return np.unravel_index(indices, ary.shape) # 0 - row, 1 - column

    def templates_topo_temp_n(self, save=True, return_temp=False):
        """ Plot topography for template n"""
        """ For even N_t don't forget +1 """
        """
        This code is too slow....
        from mne.viz import iter_topography        
        
        ymin,ymax = temp_i.min(), temp_i.max()         
        for ax, idx in iter_topography(self.data_info_sens, fig_facecolor='white', axis_facecolor='white', axis_spinecolor='white', on_pick=None): #my_callback
            if idx in sensors: ax.plot(temp_i[idx],linewidth=0.5, color='red')
            else: ax.plot(temp_i[idx],linewidth=0.5, color='blue')
            ax.set_ylim([ymin+ymin/5,ymax+ymax/5])      
            
        sensors, time = Templates.largest_indices(np.abs(temp_i), 1)
        self.pick_index = sensors[0]
        self.pick = self.data_info['ch_names'].index(self.data_info_sens['ch_names'][self.pick_index])
        """
        
        from circus.shared.files import load_data
        import numpy as np
        import mne
        
        N_e = self.params.getint('data', 'N_e') # The number of channels
        N_t = self.params.getint('detection', 'N_t')+1 # The temporal width of the template #sometimes needs +1 !!!!!
        templates_cir = load_data(self.params, 'templates')

        temp_i = templates_cir[:, self.temp_n].toarray().reshape(N_e, N_t)
        self.temp_n_evocked = mne.EvokedArray(temp_i, self.data_info_sens)
        self.pick_name = self.temp_n_evocked.get_peak()[0]
        self.pick = self.data_info['ch_names'].index(self.pick_name)
        
        fig = self.temp_n_evocked.plot_topo(vline=None, legend=False, show=False)
        fig.suptitle('Template %s'%self.temp_n, x=0.42)
        if save:
            fname = "%s%s_templates_topo.svg"%(self.svg_path, self.temp_n)
            fig.savefig(fname, format='svg', papertype='legal')
        else: self.templates_topo_temp_n_fig = fig
        fig.clf()
        plt.close(fig)
        
        if return_temp:
            return self.temp_n_evocked

        del templates_cir, N_e, N_t

    def power_plot_temp_n(self,save=False):
        """ Power plot for template n"""
        import numpy as np
        from mne.time_frequency import tfr_multitaper #(tfr_multitaper, tfr_stockwell, tfr_morlet, tfr_array_morlet)
        freqs = np.arange(1., 60., 1)
        n_cycles = freqs/10.
        time_bandwidth = 2.0
        power = tfr_multitaper(self.epochs_temp,freqs=freqs, n_cycles=n_cycles, time_bandwidth=time_bandwidth, picks=[self.pick], return_itc=False, verbose=False)
        # Plot results. Baseline correct based on first 100 ms.
        fig = power.plot([0],  mode='mean', title='Time-Frequency Representation', show=False) #baseline=(-1,-0.9),
        #f = power.plot_topomap(baseline=(-1., -0.9), ch_type = 'mag')
        if save:
            fname = "%s%s_power_plot.svg"%(self.svg_path, self.temp_n)
            fig.savefig(fname, format='svg', papertype='legal')
        else: self.power_plot_temp_n_fig = fig
        #fig.clf()
        plt.close(fig)
        del power, time_bandwidth, n_cycles, freqs
        
    def _order_func(times, data):
        import numpy as np
        import random
        from sklearn.cluster.spectral import spectral_embedding  # noqa
        from sklearn.metrics.pairwise import rbf_kernel   # noqa
        this_data = data[:, (times > 0.0) & (times < 0.350)]
        this_data /= np.sqrt(np.sum(this_data ** 2, axis=1))[:, np.newaxis]
        return np.argsort(spectral_embedding(rbf_kernel(this_data, gamma=1.), n_components=1, random_state=0).ravel())

    def plot_epochs_image_temp_n(self, save=False):
        """ Epochs image for template n"""
        import mne
        import os
        self.epochs_temp.filter(1., 45., fir_design='firwin')
        mne.viz.plot_epochs_image(self.epochs_temp, [self.pick], order=Templates._order_func, colorbar=True,  show=False)
        if save:
            fname = "%s%s_epochs_image.svg"%(self.svg_path, self.temp_n)
            plt.savefig(fname, dpi=50, format='svg', papertype='legal')
        else:
            fig = plt.gcf()
            self.plot_epochs_image_temp_n_fig = fig
        plt.close()

        #for i in range(len(self.epochs_temp)):
        #    epochs_temp_0 = self.epochs_temp[i]
        #    epochs_temp_0.average().pick_types(meg='grad').plot_topo(background_color='w',vline=self.vlines[i],title='Templeat №{}'.format(self.temp_n))

        #    os.makedirs('%sSpikes/'%(self.svg_path),exist_ok=True)
        #    fname = "%sSpikes/temp_%s_topo_%s.png"%(self.svg_path,self.temp_n,i)
        #    plt.savefig(fname, format='png', papertype='legal', dpi=450)
        #    fig = plt.gcf()
        #    plt.close(fig)
        #    del epochs_temp_0
        #plt.close()
        
    def save_waveform_temp_n(self):
        """ Make average and save waveforms for epochs template n"""
        self.evoked_grad = self.epochs_temp.average().pick_types(meg='grad')
        self.evoked_mag = self.epochs_temp.average().pick_types(meg='mag')
        self.epochs_temp.average(picks=self.pick).save('%s%s/Templates_waveforms/%s.fif'%(self.folder, self.output_dir,self.template))
        
    def plot_evoked_joint_temp_n(self, save=False):
        """ Make evocked plot for epochs template n"""
        import mne
        import numpy as np
        mne.viz.plot_evoked_joint(self.evoked_mag, times=np.array([-0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2]), show=False)
        if save:
            fname = "%s%s_evoked_joint_mag.svg"%(self.svg_path, self.temp_n)
            plt.savefig(fname, format='svg', papertype='legal')
        else:
            fig = plt.gcf()
            self.plot_evoked_joint_temp_n_mag_fig = fig
        plt.close(fig)
        
        mne.viz.plot_evoked_joint(self.evoked_grad, times = np.array([-0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2]), show=False)
        if save:
            fname = "%s%s_evoked_joint_grad.svg"%(self.svg_path, self.temp_n)
            plt.savefig(fname, format='svg', papertype='legal')
        else:
            fig = plt.gcf()
            self.plot_evoked_joint_temp_n_grad_fig = fig
        plt.close(fig)
        
    def time_between_spikes_temp_n(self, save=False):
        """ Make time different for spikes template n"""
        from circus.shared.files import load_data
        import numpy as np
        results = load_data(self.params, 'results')
        fig, ax = plt.subplots(figsize=(4,2.9))
        spikes = results['spiketimes'][self.template]/1000
        isis = np.diff(spikes)

        plt.hist(isis, bins=100, range=(0,3))
        ax.set_ylabel("Spikes")
        ax.set_xlabel("Time, s")
        if save:
            fname = "%s%s_time_between_spikes.svg"%(self.svg_path, self.temp_n)
            plt.savefig(fname, format='svg', papertype='legal')
        else: self.time_between_spikes_temp_n_fig = fig
        plt.close(fig)

    def spikes_distribution_temp_n(self, save=False):
        """ Make distribution for spikes template n"""
        from circus.shared.files import load_data
        results = load_data(self.params, 'results')
        fig, ax = plt.subplots(figsize=(9,2.9))
        spikes = results['spiketimes'][self.template]/1000
        amps = results['amplitudes'][self.template][:, 0] # The second column are amplitude for orthogonal, not needed
        plt.plot(spikes, amps, '.')
        ax.set_ylabel("Amplitudes")
        ax.set_xlabel("Time, s")
        if save:
            fname = "%s%s_spikes_distribution.svg"%(self.svg_path, self.temp_n)
            plt.savefig(fname, format = 'svg', papertype= 'legal')
        else:
            fig = plt.gcf()
            self.spikes_distribution_temp_n_fig = fig
        plt.close(fig)
        
    def _waitForResponse(x): 
        out, err = x.communicate() 
        if x.returncode < 0: 
            r = "Popen returncode: "+str(x.returncode) 
            raise OSError(r)

    def plot_final_temp_n(self, system_type='Windows'):
        """ Plot all plots in one"""
        import svgutils.transform as sg
        from subprocess import Popen
        fig = sg.SVGFigure("24cm", "25cm")
        #plot1 = sg.fromfile("%s%s_epochs_image.svg"%(self.svg_path, self.temp_n)).getroot()
        plot1 = sg.from_mpl(self.plot_epochs_image_temp_n_fig).getroot()
        plot1.moveto(10, 10)
        #plot2 = sg.fromfile("%s%s_evoked_joint_mag.svg"%(self.svg_path, self.temp_n)).getroot()
        plot2 = sg.from_mpl(self.plot_evoked_joint_temp_n_mag_fig).getroot()
        plot2.moveto(20, 285)
        plot2.scale_xy(0.7, 0.7)
        #plot3 = sg.fromfile("%s%s_evoked_joint_grad.svg"%(self.svg_path, self.temp_n)).getroot()
        plot3 = sg.from_mpl(self.plot_evoked_joint_temp_n_grad_fig).getroot()
        plot3.moveto(20, 500)
        plot3.scale_xy(0.7, 0.7)
        plot4 = sg.fromfile("%s%s_templates_topo.svg"%(self.svg_path, self.temp_n)).getroot()
        #plot4 = sg.from_mpl(self.templates_topo_temp_n_fig).getroot()
        plot4.moveto(440, 20)
        plot4.scale_xy(1.2, 1.1)
        plot5 = sg.fromfile("%s%s_power_plot.svg"%(self.svg_path, self.temp_n)).getroot()
        #plot5 = sg.from_mpl(self.power_plot_temp_n_fig).getroot()
        plot5.moveto(440, 340)
        plot5.scale_xy(1.2, 1.3)
        #plot6 = sg.fromfile("%s%s_spikes_distribution.svg"%(self.svg_path, self.temp_n)).getroot()
        plot6 = sg.from_mpl(self.spikes_distribution_temp_n_fig).getroot()
        plot6.moveto(290, 715)
        #plot6.scale_xy(1.5, 1.)
        #plot7 = sg.fromfile("%s%s_time_between_spikes.svg"%(self.svg_path, self.temp_n)).getroot()
        plot7 = sg.from_mpl(self.time_between_spikes_temp_n_fig).getroot()
        plot7.moveto(20, 715)
        #plot7.scale_xy(1.5, 1.)

        params_plot_fin = ['channels = %s'%self.sensors, 'filtering = %s-%s Hz'%(self.cut_off, self.cut_off_top), 
                           'N_t = %s ms'%self.N_t, 'spike_thresh = %s'%self.spike_thresh,'isolation = False', 
                           'cc_merge = %s'%self.cc_merge, 'cc_overlap = 0.4', 'amp_limits = auto','safety_time = 1ms', 'cc_mixtures = 0.6']
        l = []
        for i in range(len(params_plot_fin)):
            l.append(sg.TextElement(815,27 + i*7, params_plot_fin[i], size=5))

        l.append(sg.TextElement(20,20, "A", size=12, weight="bold"))
        l.append(sg.TextElement(20,300, "B", size=12, weight="bold"))
        l.append(sg.TextElement(20,530, "C", size=12, weight="bold"))
        l.append(sg.TextElement(440,20, "D", size=12, weight="bold"))
        l.append(sg.TextElement(440,350, "E", size=12, weight="bold"))
        l.append(sg.TextElement(800,15, "N events: %s" %self.n_spikes, size=10) )
        l.append(sg.TextElement(20,730, "F", size=12, weight="bold"))
        l.append(sg.TextElement(310,730, "G", size=12, weight="bold"))

        fig.append([plot1, plot2, plot3, plot4, plot5, plot6, plot7])
        fig.append(l)
        fig.save("%s%s_fig_final.svg"%(self.svg_path, self.temp_n))

        your_svg_input = "%s%s_fig_final.svg"%(self.svg_path, self.temp_n)
        your_png_output = "%s%s_temp.png"%(self.png_path, self.temp_n)

        if system_type == 'Mac':
            x = Popen(['/Applications/Inkscape.app/Contents/Resources/bin/inkscape', your_svg_input, \
                       '--export-png=%s' % your_png_output, '-w2000 -h3000', '-b white'])
        elif system_type == 'Windows':
            x = Popen(['C:/Program Files/Inkscape/inkscape', your_svg_input, \
                       '--export-png=%s' % your_png_output, '-w2000 -h3000', '-b white'])
        try:
            Templates._waitForResponse(x)
        except OSError:
            return False
    
    def plot_all_temp_n(self, epochs, tmp_name, system_type='Windows'):
        """ Plot all plots for template n"""
        import traceback
        #with NoStdStreams():
        try:
            self.read_templates()
            self.all_temp_barplot()
            self.best_spikes_temp_n(tmp_name)
            self.create_epochs_temp_n(epochs)
            self.templates_topo_temp_n()
            with NoStdStreams():
                self.power_plot_temp_n(save=True)
            self.plot_epochs_image_temp_n()
            self.save_waveform_temp_n()
            self.plot_evoked_joint_temp_n()
            self.spikes_distribution_temp_n()
            self.time_between_spikes_temp_n()
            self.plot_final_temp_n(system_type)
        except Exception: traceback.print_exc()

    def plot_all_templates(self, epochs_file, system_type='Windows'):
        """ Plot all templates """
        from ipypb import track
        import mne
        
        epochs = mne.read_epochs(epochs_file, preload=False, verbose=False)
        for t_name in track(self.main_temp_names, label='Templates '):
            self.plot_all_temp_n(epochs, t_name, system_type)
        
        del epochs
