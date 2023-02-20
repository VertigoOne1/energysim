import { Component } from '@angular/core';

@Component({
  //selector: 'app-nav', Use like a div <app-nav></app-nav>
  //selector: '[app-nav]', Use as attribute <div app-nav></div>
  selector: '.app-nav', //Use as a css style class

  templateUrl: './nav.component.html',
  styleUrls: ['./nav.component.css']
})
export class NavComponent {

  siteName: string = 'Shopping'

}
