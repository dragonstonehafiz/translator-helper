import { Routes } from '@angular/router';
import { HomeComponent } from './pages/home/home.component';
import { SettingsComponent } from './pages/settings/settings.component';
import { LibraryComponent } from './pages/library/library.component';
import { LibraryDetailComponent } from './pages/library/library-detail/library-detail.component';
import { TranscribeComponent } from './pages/transcribe/transcribe.component';
import { TranslateComponent } from './pages/translate/translate.component';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'settings', component: SettingsComponent },
  { path: 'library', component: LibraryComponent },
  { path: 'library/:seriesId', component: LibraryDetailComponent },
  { path: 'transcribe', component: TranscribeComponent },
  { path: 'translate', component: TranslateComponent },
  { path: '**', redirectTo: '' }
];
