import { Routes } from '@angular/router';
import { HomeComponent } from './pages/home/home.component';
import { SettingsComponent } from './pages/settings/settings.component';
import { ContextComponent } from './pages/context/context.component';
import { TranscribeComponent } from './pages/transcribe/transcribe.component';
import { TranslateComponent } from './pages/translate/translate.component';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'settings', component: SettingsComponent },
  { path: 'context', component: ContextComponent },
  { path: 'transcribe', component: TranscribeComponent },
  { path: 'translate', component: TranslateComponent },
  { path: '**', redirectTo: '' }
];
