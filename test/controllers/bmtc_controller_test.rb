require 'test_helper'

class BmtcControllerTest < ActionDispatch::IntegrationTest
  test "should get getPrice" do
    get bmtc_getPrice_url
    assert_response :success
  end

end
