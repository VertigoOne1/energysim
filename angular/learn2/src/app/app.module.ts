import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppComponent } from './app.component';
import { containerComponent } from './container/container.component';
import { NavComponent } from './nav/nav.component';
import { HeaderComponent } from './header/header.component';
import { NotificationComponent } from './notification/notification.component';
import { SearchComponent } from './search/search.component';
import { FormsModule } from '@angular/forms';

@NgModule({
  declarations: [
    AppComponent,
    containerComponent,
    NavComponent,
    HeaderComponent,
    NotificationComponent,
    SearchComponent
  ],
  imports: [
    BrowserModule,
    FormsModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
