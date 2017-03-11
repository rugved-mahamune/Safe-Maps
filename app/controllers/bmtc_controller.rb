class BmtcController < ApplicationController
  include BmtcHelper
  def getPrice
  	@res
  	@cost
  	require 'net/http'
  	require 'nokogiri'
  	url = URI.parse('https://narasimhadatta.info/cgi-bin/find.cgi')
  	https = Net::HTTP.new(url.host,url.port)
  	@req = Net::HTTP::Post.new(url.to_s, initheader = {'Content-Type' =>'application/x-www-form-urlencoded'})
  	https.use_ssl = true
  	@req.set_form_data('route' => '43')
  	@res = https.request(@req)
  	body = @res.body.gsub('</li>\n\t\t','')
  	html_doc = Nokogiri::HTML(@res.body)
  	bubu = html_doc.xpath("//li")
  	@lulu = bubu.to_s.split("<li>")
  	@priceList =[0,5,12,14,17,19,19,20,21,22,23,23,24,24,25,25,25,25,25,26,27,27,29,29,30,30,31,31,31,32,32,32,33,33,33,34,34,34,35,35,35,36,36,36,37,37,37,38,38,39,39,39,40,40,40,41,41,41,42,42,42,43,43,43,44,44,44]
	@list = BmtcHelper.remove_tags(@lulu)
	@list = eval(@list)
	if @list.include?('Corporation') and @list.include?('Seetha Circle')
		stages = @list.index('Seetha Circle') - @list.index('Corporation')
		@cost = @priceList[stages]
	end
  end
end
